from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import archive


@pytest.fixture
def root(tmp_path, monkeypatch):
    notes = tmp_path / 'notes'
    notes.mkdir()
    monkeypatch.setattr(archive, 'notes_path', str(notes))
    monkeypatch.setattr(archive, 'archive_documents_path', str(notes / '_archive_data/documents'))
    return notes


def test_identity_metadata_and_repeated_reload(root):
    path = Path(archive.save_note('First', 'one', 'body', 'nested/valid', 'A,a'))
    path.write_text(path.read_text().replace('\n\n', '\nCustom: keep: this\n\n'))
    original_id = archive.load_notes()[0]['meta']['note_id']
    for title in ['Second', 'Third']:
        archive.update_note(str(path), title, 'two', 'changed', 'B,b')
        note = archive.load_notes()[0]
        assert note['meta']['note_id'] == original_id
        assert note['meta']['custom'] == 'keep: this'
        assert note['title'] == title
        assert note['tags'] == ['two'] and note['aliases'] == ['b']
        assert note['body'] == 'changed'


def test_legacy_edit_does_not_invent_identity(root):
    path = root / 'legacy.md'
    path.write_text('title: Old\ncustom: keep\n\nbody\n')
    archive.update_note(str(path), 'New', '', 'new')
    note = archive.load_notes()[0]
    assert note['meta'] == {'custom': 'keep'}


@pytest.mark.parametrize('category', ['../outside', 'a/../../outside', '/tmp/outside', r'a\..\outside', '%2e%2e/outside', '%252e%252e/outside', 'a//b', 'a/./b'])
def test_reject_unsafe_categories(root, category):
    with pytest.raises(ValueError):
        archive.save_note('Unsafe', '', 'body', category)
    assert list(root.iterdir()) == []


def test_symlink_creation_and_edit_escape(root, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    target = outside / 'note.md'
    target.write_text('title: Keep\n\noriginal\n')
    before = target.read_bytes()
    (root / 'linked').symlink_to(outside, target_is_directory=True)
    (root / 'note.md').symlink_to(target)
    for category in ['linked', 'linked/nested']:
        with pytest.raises(ValueError):
            archive.save_note('note', '', 'bad', category)
    for path in [root / 'note.md', root / 'linked/note.md', target, root / '../outside/note.md']:
        with pytest.raises(ValueError):
            archive.update_note(str(path), 'bad', '', 'bad')
    assert target.read_bytes() == before
    assert not (outside / 'nested').exists()


def test_collision_preserves_bytes_and_concurrent_creation(root):
    def create(_):
        try:
            return archive.save_note('Same', '', 'original', '')
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create, range(8)))
    assert sum(r is not None for r in results) == 1
    path = root / 'same.md'
    before = path.read_bytes()
    with pytest.raises(FileExistsError, match='already exists'):
        archive.save_note('Same', '', 'replace', '')
    assert path.read_bytes() == before


def test_new_ids_do_not_collide_after_rename(root):
    first = archive.save_note('X', '', 'one', 'a')
    archive.update_note(first, 'Y', '', 'one')
    archive.save_note('X', '', 'two', 'b')
    ids = [n['meta']['note_id'] for n in archive.load_notes()]
    assert len(set(ids)) == 2


def test_hardlink_edit_rejected(root, tmp_path):
    import os
    outside = tmp_path / 'outside.md'
    outside.write_text('title: Keep\n\nbody\n')
    os.link(outside, root / 'linked.md')
    with pytest.raises(ValueError):
        archive.update_note(str(root / 'linked.md'), 'bad', '', 'bad')
    assert outside.read_text() == 'title: Keep\n\nbody\n'


def test_final_symlink_creation_collision(root, tmp_path):
    outside = tmp_path / 'outside.md'
    outside.write_bytes(b'keep')
    (root / 'same.md').symlink_to(outside)
    with pytest.raises(FileExistsError):
        archive.save_note('Same', '', 'bad', '')
    assert outside.read_bytes() == b'keep'


def test_ui_collision_and_unsafe_category(root):
    from app import app
    client = app.test_client()
    data = {'title': 'Same', 'body': 'original', 'category': 'nested'}
    assert client.post('/add', data=data).status_code == 302
    before = (root / 'nested/same.md').read_bytes()
    response = client.post('/add', data={**data, 'body': 'replacement'})
    assert response.status_code == 409
    assert b'different title/category' in response.data
    assert (root / 'nested/same.md').read_bytes() == before
    assert client.post('/add', data={**data, 'category': '../escape'}).status_code == 400


def test_metadata_cannot_inject_identity(root):
    with pytest.raises(ValueError):
        archive.save_note('title\nnote_id: injected', '', 'body', '')
    assert list(root.iterdir()) == []


def test_symlink_loop_is_actionable(root):
    (root / 'loop').symlink_to('loop', target_is_directory=True)
    with pytest.raises(ValueError):
        archive.save_note('No', '', 'body', 'loop')


def test_ui_reopen_edit_and_identity(root):
    from app import app
    client = app.test_client()
    response = client.post('/add', data={'title': 'First', 'body': 'first', 'category': 'a/b'})
    assert response.status_code == 302
    persistent_id = archive.load_notes()[0]['meta']['note_id']
    for body in ['second', 'third']:
        # A fresh client/cache reload represents reopening the application.
        client = app.test_client()
        assert client.get('/').status_code == 200
        note = archive.load_notes()[0]
        assert client.post(f'/edit/{note["id"]}', data={'title': 'Edited', 'body': body}).status_code == 302
        saved = archive.load_notes()[0]
        assert saved['body'] == body
        assert saved['meta']['note_id'] == persistent_id
        assert client.get(f'/api/note/{persistent_id}').status_code == 200


def test_component_swap_to_symlink_before_open(root, tmp_path, monkeypatch):
    import os
    outside = tmp_path / 'outside'
    outside.mkdir()
    (root / 'category').mkdir()
    original_open = os.open
    swapped = False
    def swap(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == 'category' and not swapped:
            swapped = True
            (root / 'category').rmdir()
            (root / 'category').symlink_to(outside, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', swap)
    with pytest.raises(ValueError):
        archive.save_note('No', '', 'body', 'category')
    assert list(outside.iterdir()) == []
