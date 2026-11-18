# WO-003 — note integrity and filesystem safety

Base: main `c1dd66cb35afe163a6ff7ee24b65552c7d5d0b93` (WO-001 merged).
Initial implementation preceded PR #45 merging. Integration now incorporates
main `5411fe5093b54d880ad96481dd907baf2507be2e`, including WO-002 infrastructure
and AGENTS.md. The implementation and regression tests are preserved. Only Archive note operations, their route errors and
regressions changed.

## Behavior

Updates preserve raw unknown header fields and persistent IDs, including after
repeated edits/reloads. Legacy notes without IDs stay that way. New authored
notes get UUID-based IDs; existing notes are not bulk migrated. Title/tags/aliases
remain editable and cannot inject additional metadata lines.

Creation rejects existing filenames (including symlinks) using exclusive file
creation, with HTTP 409 and instructions to edit or choose another destination.
It does not rename or replace automatically. Canonical containment is combined
with Linux directory-descriptor traversal and O_NOFOLLOW opens, so replacing a
component with a symlink between validation and open cannot redirect writes.
Edits require an existing regular, singly-linked file under the configured root.
Symlinks (even within the root), hard links, traversal, absolute categories,
backslashes, residual percent encodings, and empty/dot path components are
rejected. Ordinary slash-separated nested categories remain supported. HTTP
form decoding occurs once in Flask; no extra URL decoding is applied to paths.

## Executed evidence

Linux, Python 3.12.14; development versions installed fresh from PR #45 commit
`90ad887b7f4ad3b8e48f449c1505a907c4f88156:requirements-dev.lock`.

- Original main extracted into a disposable directory: `python -m pytest -q`:
  **185 passed in 0.74s**.
- Initial 13 new cases against original implementation: **13 failed in 0.08s**,
  exposing metadata/ID loss, unsafe category acceptance, link handling and
  overwrite/collision behavior. Only disposable fixtures were used.
- First corrected suite: **198 passed in 0.75s**.
- Expanded suite via borrowed WO-002 verifier: **202 passed in 0.77s**.
- Final suite via the same verifier: **205 passed in 0.99s**, no failures/skips;
  `pip check`: **No broken requirements found**.

Final command (absolute paths vary per checkout):

```bash
PYTHON_BIN=/workspace/scratch/727ab565ddbc/wo003-venv/bin/python bash scripts/verify.sh /workspace/scratch/727ab565ddbc/wo003-final-results
```

The verifier was temporarily materialized from PR #45 without staging it, and
removed after execution. New source/tests were staged so its tracked-source
copy included them. JUnit, dependency and test logs were generated. This PR adds
20 cases covering persistence, legacy compatibility, unsafe paths, symlinks and
component swaps, hard links, byte-preserving collisions, eight concurrent
creators, UI errors/reopen and metadata injection. No assertions were weakened.

## Review, limits and CI

Separate reviewer `/root/wo003_review` inspected data preservation, filesystem
opens, metadata compatibility, race protection, tests and scope. Initial review
found no blockers and recommended actionable symlink-loop errors. That change
and regression were included in a bounded follow-up review. Final review and
candidate CI status are recorded in the PR description.

WO-002 is now merged. The existing WO-003 branch incorporates latest main
without changing application implementation or regression assertions. The actual
tracked `scripts/verify.sh` is used for integration verification. Candidate SHA,
executed results, separate integration review and hosted CI outcome are recorded
in the existing PR #46 description. Historical borrowed-verifier results above
remain evidence of the initial implementation, not substitute candidate CI.

This is not crash-atomic saving or concurrent-edit conflict detection. As before,
a failed write can leave an incomplete file, and simultaneous edits can conflict.
Directory-descriptor checks resist symlink substitution but do not sandbox a
hostile local process with permission to relocate already-open directories or
rewrite note content. No full hostile-filesystem security certification is
claimed. Existing malformed/duplicate IDs are preserved, not repaired. Read-side
symlink policy and ingestion paths are unchanged. WO-004 HTML fixes are excluded.

## Human acceptance

Use disposable notes. Create one in a nested category, record its note_id, edit
title/tags/aliases/body, close/reopen Archive, and edit again. Confirm content,
ID and any custom metadata remain. Attempt the same original title/category
again: expect a clear collision message and unchanged existing bytes. Check an
ordinary legacy note still edits. No personal corpus migrations are required.
Merge remains human-controlled. Reverting the code restores old behavior but
must not rewrite or revert user notes created/edited during acceptance.
