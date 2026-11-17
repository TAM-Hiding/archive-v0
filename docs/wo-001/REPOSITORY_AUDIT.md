# Repository audit — TAM WO-001

Audited 2026-11-17. Scope: accessible default branches, not outstanding feature PRs or the user's local installations. Application source was not modified. This audit is not a penetration test or an exhaustive correctness proof.

## Pinned repository state

| Repository | Default | Audited SHA | Local verification | Remote CI observation |
|---|---|---|---|---|
| [archive-v0](https://github.com/TAM-Hiding/archive-v0) | main | `efb3b06419b815b40e8fc24e68f6afe5c0fcfd5b` | 185 tests passed; three separate safety/integrity probes reproduced gaps | API returned zero Actions runs |
| [hero-cad](https://github.com/TAM-Hiding/hero-cad) | main | `56983d35ae255365462361baeb89cdc851ac32b4` | 172 selected tests passed; 950 collected; pinned editable install and pip check passed | Audited default SHA has recorded successful two-OS Tests run |
| [requisition-denied](https://github.com/TAM-Hiding/requisition-denied) | main | `a362667fa7ce8942c234e56e3936cd42ed89e384` | Required 4.7.2 unavailable; 4.6.3 compatibility checks include configuration and scrap failures | API returned zero Actions runs |

Default refs came from fresh clones and origin/HEAD. Archive API also confirmed main/default head and write permission. References below are relative to the named repository at these exact commits. The historical memory of 86 Archive tests, intersection-aware CAD regions and RD-010 is not evidence of current default-branch behavior.

### Evidence interpretation

Static inspection verifies what code/config says. Executed results are labeled with commands and limitations. Remote results are observations of GitHub's reporting, not local reruns. Architectural risks are inferences, proposals are recommendations, and unanswered questions remain unresolved. No numeric coverage percentage is claimed for CAD or RD.

GitHub Actions API queried `/repos/TAM-Hiding/{repo}/actions/runs?per_page=3`: Archive and RD returned total_count 0; CAD returned total_count 261. CAD [run 42564040049](https://github.com/TAM-Hiding/hero-cad/actions/runs/42564040049), at the audited SHA, reports success for Ubuntu 22.04 and 24.04, including dependency install, pip check and full Xvfb pytest steps. More recent runs 42564580457 and 42564536887 succeeded at a different SHA (`0e9a3ecc320be322410f2d43c1924bb8450bc762`); they are not substituted for the default baseline. No test counts were inferred from remote status.

Archive's branch API reported main `protected: false`; this does not establish the absence of all rulesets or external policy. No settings were changed. Full repository security settings, secrets, billing, runner configuration and installed applications were not audited.

## Overall conclusion and priority

Preserve the existing architectures. HERO-CAD already has strong automated gates. Archive and RD have useful test suites but lack routine CI. First establish reproducible baselines; immediately address Archive's demonstrated note identity/path/rendering defects. Add target-version RD CI and modest CAD packaging/evidence improvements. Shared Archive access and durable Nexus orchestration depend on explicit contracts and policy, not wholesale application rewrites.

Recommendations and approval/cost ledgers are in [ENGINEERING_WORKFLOW](ENGINEERING_WORKFLOW.md), [ARCHIVE_EVOLUTION](ARCHIVE_EVOLUTION.md), [AGENT_ORCHESTRATION](AGENT_ORCHESTRATION.md) and [IMPLEMENTATION_ROADMAP](IMPLEMENTATION_ROADMAP.md). The repository sections retain their supporting evidence below.


## Archive audit evidence — WO-001

Audit date: 2026-11-17. Repository `TAM-Hiding/archive-v0`, cloned default branch `main`, SHA `efb3b06419b815b40e8fc24e68f6afe5c0fcfd5b`. Findings refer to this SHA, not outstanding PRs. No tracked source was modified; `git status --short` clean after inspection/test/probes. 80 tracked files. No AGENTS.md in this repository; no tracked `.github` workflows, lockfiles, pyproject/setup packaging configuration. Repository write/CI service permissions are outside this sub-audit.

### Architecture and strengths (verified by source inspection)

- Local Flask/Jinja browser UI in `app.py` (545 lines), core filesystem notes/search/curation in `archive.py` (1,962 lines); separate `ingestion/` functions for registry, extraction, cleanup, chunking, indexing, tables, figures and source previews. `ingest.py:50–139` composes the pipeline. `ingestion/chunkers.py` is 1,776 lines and is a substantial heuristic subsystem.
- Source PDF copied with `shutil.copy2`, separate from derived artifacts (`ingestion/registry.py:54–107`). Source filename, original path, archive location, document ID and extraction metadata already exist. This is a useful incremental foundation, not justification for a rewrite.
- Notes are Markdown with a lightweight custom metadata header; registry and structural/layout files are JSON. Runtime data is ignored by Git (`.gitignore`, `notes/`). No actual user source corpus was available in this clone.
- PDF geometric extraction defaults to pdfplumber with explicit pypdf fallback. Page markers retain PDF viewer page numbering (`ingestion/extractors.py:42–56,60–113`). Structural entries preserve viewer pages, printed page labels/estimates, semantic IDs and text spans (`ingestion/structural_index.py:8–61`). Do not conflate printed and PDF pages.
- `ingest.py:18–48,98–125`: auto storage switches above 300 chunks to structural-only representation; table/figure sidecar shards and lazy source-page previews limit persisted output. This does NOT establish bounded ingestion memory: extractors accumulate all pages and joined text, and ingest constructs all chunks before choosing storage mode.
- Original-PDF resolution rejects path escape via realpath/commonpath (`archive.py:1283–1311`). Original pages remain inspectable where flattened extraction is ambiguous. Table-cell API returns value and provenance; existing tests cover numeric table recovery.
- Re-extraction computes before replacing and backs up metadata/text/index (`reextract_structure.py:56–104`). Rebuild, table-shard migration and figure extraction have regression tests. These are good precedents, but not a transaction or tested full rollback protocol.
- Existing JSON read endpoints cover stable note ID lookup, document metadata, structure, segments and table cells (`app.py:109–120,352–394`). No versioned service contract or agent authorization middleware observed. Search currently lives in UI/core functions, not a versioned retrieval endpoint.

### Verification actually executed

Initial `python3 -m pytest -q` failed immediately because the provided Python had no pytest. Created an isolated sibling virtualenv; installed `requirements.txt` plus audit-only `pytest-cov`. No dependency files changed.

Environment: Linux, Python 3.12.14; Flask 3.1.3, pdfplumber 0.11.10, pypdf 7.1.0, pytest 9.2.0, pytest-cov 7.1.0. Full resolved environment retained in `/workspace/scratch/727ab565ddbc/archive-audit-requirements.txt`.

Executed from repository root:

```bash
COVERAGE_FILE=/workspace/scratch/727ab565ddbc/archive-audit.coverage \
/workspace/scratch/727ab565ddbc/archive-audit-venv/bin/python -m pytest -q \
  --cov=archive --cov=app --cov=ingest --cov=ingestion \
  --cov=rebuild_structure --cov=reextract_structure \
  --cov=extract_table_layout --cov=extract_figure_layout --cov=shard_table_layout \
  --cov-report=term --junitxml=/workspace/scratch/727ab565ddbc/archive-tests.xml
```

**Result: 185 passed in 11.33 seconds.** No skips or failures reported. Output `/workspace/scratch/727ab565ddbc/archive-tests.log`. This supersedes historical 86-test counts.

Coverage: reported statement coverage 73% over 3,177 measured statements in imported targets; app.py 40%, archive.py 62%, chunkers 91%, cleaners 98%, extractors 93%, registry 96%, table_layout 92%. **Not whole-repository coverage:** tool warned that ingest.py was never imported; ingest.py and unmeasured tools/ scripts are excluded from the denominator. Branch coverage was not enabled. Tests often use tmp_path, synthetic PDFs and monkeypatches. Passing them does not verify the real Handbook corpus, end-to-end ingestion, concurrent access, long-document memory bounds, actual browser appearance, or production authorization.

Three additional disposable-data probes ran against original code (all within TemporaryDirectory; no retained user data):

1. `save_note` created a note containing note_id; `update_note` removed note_id. Observed outputs `new note had note_id: True`, `edited note retained note_id: False`.
2. `save_note(..., category='../outside')` resolved outside the configured notes root. Observed `category escaped configured notes root: True`.
3. Flask test-client POST search rendered inert `<b data-audit="probe">raw markup</b>` from note text unescaped; HTTP 200. No executable payload/browser exploitation attempted. This verifies unsafe HTML rendering, with script injection risk inferred from the same path.

### Existing tests and gaps

- pytest configured in `pytest.ini`; 26 test modules cover extraction, chunking, paths, registry, notes index, search, structure/segments/actions, document details, figure/table layout, original access/previews, rebuild/reextract/sharding, UI templates.
- `tests/test_registry.py:6–32` checks record creation and paths but not source byte hashes. `tests/test_reextract_structure.py:6–75` checks backup presence with mocked extraction/chunking/indexing, not multi-file crash recovery.
- No CI tracked. No unit/integration command documented in README. README project tree misleadingly shows root `test_*.py` and missing CHANGELOG.md; actual tests are under tests/. README is otherwise detailed about extraction features, source viewing, and CLI usage.
- `requirements.txt:1–4` contains only unpinned Flask/pdfplumber/pypdf/pytest; runtime/test requirements mixed; no supported Python declaration or packaged distribution. Linux launcher uses ambient `python3`, curl, xdg-open; starts Flask with nohup and readiness poll (`launch_archive.sh:5–40`). No build artifact workflow. Actual launcher/browser test not executed.
- No AGENTS or PR template convention present in snapshot. Developer conventions must currently be provided externally; do not infer CI enforcement or branch protections from absence of workflow files.
- Manual acceptance should remain for varied real PDFs, tables/equations/diagrams and source citation accuracy, document navigation and presentation. Prefer small permission-safe synthetic fixture PDFs for CI; keep copyrighted/user corpus outside public repository.

### Risks and recommended order

#### A1 — Local content integrity and path containment (high priority)

Verified: `archive.py:1763–1770` joins category after only strip operations, unlike validated ingestion paths; traversal probe succeeds. Same slug creation opens with `w` (`1786`) and can silently overwrite an existing note. `update_note:1796–1814` rewrites only title/tags/aliases/body, dropping stable IDs and unknown metadata. API note resolution depends on that ID (`147–157`), and UI edits use load-order integer IDs (`app.py:440–490`; `archive.py:125–140`). Reindexing deletes generated output before replacement (`ingestion/indexer.py:150–167`). These deserve focused regression tests and small fixes before shared/agent write access. Expected benefit: protect existing authored content and references. Complexity/maintenance: low-to-medium, modest. Dependencies: baseline verification command. Risk: compatibility with legacy paths/metadata. Human approval: authorize follow-up scope and merge; routine implementation delegated, collision UX decision if ambiguous; no automatic migration.

#### A2 — Trust boundary and HTML handling (high priority before remote/shared use)

Verified: README expressly states Public/Private are organization filters, not ACLs. No auth/CSRF middleware observed in app routes; `app.py:545` starts debug server; loopback URL in launcher. Search builds highlighting from raw body then `templates/index.html:260` marks preview safe (`app.py:18–28,61–86`); inert HTML probe confirms unescaped rendering. This matters even for local source ingestion. Recommendation: escape content before controlled highlights; explicit loopback/no-debug supported launch; mutation protection and real authorization before shared use. Security/privacy policy and any network exposure require product-owner approval; concrete hardening implementation can be delegated after scoped WO approval. Do not claim internet exposure is currently configured.

#### A3 — Durability, concurrency and revisioning

Verified: metadata writes open destination `w` (`registry.py:110–118`), global UI cache refresh mutates multiple globals (`app.py:8–16`), no transactional state/revision locks observed. Reextract performs separate file replacements then metadata write, leaving interrupted-update possibility. Relative CWD paths (`archive.py:1737–1739`; `ingestion/paths.py:8`) are already TODO. Recommendation: config-root abstraction and compatibility adapter; atomic single-file writes; revision check/serialized document writes; recoverable staged generations with manifest commit pointer; tested backup restore, failure injection. Cost medium, migration risk; approval for actual data migration/policy, not routine mechanics.

#### A4 — Retrieval scale and source identity

Verified: `load_notes` walks all files, search reloads structural indexes; doc lookup scans metadata (`archive.py:44–54,335–357,804–880`). Structural prose uses 220-char previews unless reconstructed, whereas table search_text stores full text (`structural_index.py:8,59–60`); test retrieval beyond preview before asserting full-text search completeness on large structural-only documents. No source digest/version/pipeline configuration schema observed. Existing semantic/index numbers can shift on rebuild and are not durable external citation identity. Recommendation: additive source digest, extraction generation/version and stable citation refs; benchmark before adding SQLite FTS index. Rebuildable index must not become source authority. Cost medium, dependency durable IDs/provenance, risk stale results and migration errors. Approval: scoped WO/merge; schema semantics/security choices owner approval where consequential.

#### A5 — Verification and confidence model

Current 'Original PDF verification' is a source-viewing UI, not a stored independent verification assertion. No explicit author-confidence/independent-verification/context applicability model observed. Add separate claim/assertion records: source+revision+span, author confidence (optional, attributed), verification status/reviewer/method/evidence/time, applicability conditions/units/version and relationships. Avoid universal confidence scores or labeling generated material verified merely because it has a citation. Cost medium; depends on stable references; risk false authority; human acceptance of product semantics required.

### Incremental evolution recommendation

Retain Flask UI, existing extractor/chunker modules, original files and Markdown. Introduce a service layer around existing functions plus explicit storage configuration; keep legacy readers and metadata fields. Stage small contracts: sources/notes/revisions/citations -> versioned retrieval API -> authorization -> optional MCP adapter. An additive SQLite catalog/FTS may be justified by measured performance and transactions, with originals and authored content preserved and exported; not a mandatory rewrite or new deployment requirement now. Store verification assertions independently from extracted source representations. Nexus should own execution/task/tool registries, capability-scoped orchestration and telemetry references; Archive owns knowledge bytes, source/citation identity, access decisions and retrieval. GitHub remains authoritative for code/PR/CI state. No Nexus implementation required by this audit.

Suggested first engineering follow-up is a small Archive baseline CI/dependency/test-command work order, followed immediately by separated content-identity/path and HTML boundary fixes; avoid postponing demonstrated defects behind speculative Nexus work.

Source browser pinned to this audit: https://github.com/TAM-Hiding/archive-v0/tree/efb3b06419b815b40e8fc24e68f6afe5c0fcfd5b


## HERO-CAD audit evidence — WO-001

Audited 2026-11-17. Repository `TAM-Hiding/hero-cad`, default clone branch `main`, commit `56983d35ae255365462361baeb89cdc851ac32b4`. Read-only source investigation; `git status --porcelain` empty after baseline checks. No application source changes. All paths below relative to this repository at that commit.

### Verified architecture

- Python 3.12 only (`>=3.12,<3.13`), setuptools package, `src/hero_cad`; PySide6 6.8.3, cadquery-ocp 7.9.3.1.1, VTK 9.6.2 pinned; pytest 8.3.5 + pytest-qt 4.4.0 (`pyproject.toml:1–30`). Console scripts are `hero-cad` and `hero-cad-install-launcher`.
- Immutable typed features/sketches + stable UUIDs; ordered transactional `Document` evaluator holds authoritative parameters and OCCT B-reps; VTK display data disposable. Separate geometry, booleans, profiles, line profiles, attachment resolution, face lineage, chamfers, persistence, tools and UI modules (`ARCHITECTURE.md:5–18`; `src/hero_cad/document.py:7–23`).
- Candidate edits retain publication baseline and reject stale candidate adoption (`document.py:25–46`). Evaluation permits 1–1000 features and exactly one base box (`document.py:80–88`). UI prepares display before candidate publication (`ui/main_window.py:628–695`), an important existing atomicity contract.
- Strict native JSON serialization currently supports versions 1–16 (`persistence.py:98–105`); construction planes/lines raise schema to 16. Save enforces 4 MiB, writes same-directory temp, flushes/fsyncs then `os.replace`; loader reads bounded size (`document.py:570–615`). Concurrent overwrite protection is not supplied by atomic replace alone.
- CURRENT DEFAULT DOES NOT INCLUDE intersection-aware planar decomposition: `line_profiles.py:39–87` explicitly rejects branches/crossings/overlaps; `profiles.py:37–47` rejects intersecting boundaries and limits analysis to 256 ordinary entities. Do not report unmerged PR49 behavior as audited default capability.

### Tests and actual execution

Isolated environment: `/workspace/scratch/727ab565ddbc/cad-venv`; CPython 3.12.14. Commands run from repository root:

1. `python3 -m venv /workspace/scratch/727ab565ddbc/cad-venv` then `<venv>/bin/pip install -r requirements-dev.lock`: successful pinned install (log `cad-install.log`).
2. `<venv>/bin/pip install --no-deps -e .`: successful editable wheel build/install (log `cad-editable.log`). This is NOT a noneditable release-wheel validation.
3. `<venv>/bin/pip check`: `No broken requirements found.`
4. `QT_QPA_PLATFORM=offscreen <venv>/bin/python -m pytest tests/test_document.py -q`: **23 passed in 0.92s**, exit 0.
5. `QT_QPA_PLATFORM=offscreen <venv>/bin/python -m pytest --collect-only -q`: **950 tests collected in 3.17s**, exit 0. Collection is not passing execution.
6. `QT_QPA_PLATFORM=offscreen <venv>/bin/python -m pytest -q tests/test_history_foundation.py tests/test_persistent_references.py tests/test_line_profiles.py tests/test_multi_profile_extrusion.py tests/test_offset_plane_orientation.py tests/test_construction_geometry.py tests/test_booleans.py tests/test_chamfers.py tests/test_regeneration_diagnostics.py`: **149 passed in 9.85s**, exit 0 (`cad-kernel.log`). This selection and test_document are disjoint: 172 local tests passed total.

No Xvfb executable was available (`command -v Xvfb` returned no path). Full GUI suite/render/startup/hardware acceptance NOT executed in this audit. No measured statement/branch coverage percentage: repository has no coverage tool/config in pyproject or CI; test-case count is not coverage. GitHub historical run evidence is reported in the audit overview; it is separate from these local executions.

#### Existing strength and coverage by inspection

- `tests/test_document.py:9–137`: kernel validity/mass/bounds, invalid dimensions, round trip, undo branching, failed regeneration/undo and atomic save failure. Meaningful numerical oracles, not only snapshots.
- History, persistent references, line loop identity, multi-profile extrusion, construction geometry, outward offset normal, Boolean, chamfer and regeneration diagnostics modules exist and selected matrix above passed.
- `tests/test_ui.py:15–72`: actual widget edit changes model volume; camera input; framebuffer checks reject blank background.
- `tests/test_files_ui.py:356–456`: injected atomic replace failure and reopen through a fresh subprocess with serialized state, kernel validity, volume and bounds. Inspected, not executed here.
- `tests/conftest.py:6–26`: per-test config/documents isolation and controlled teardown dialogs.
- 70 `test_*.py` modules (80 total files under tests, including fixtures/conftest). A broad regression suite already exists; do not describe this repository as needing testing from scratch.

### CI, build, dependencies

- `.github/workflows/tests.yml:1–19` is the only tracked workflow: push + PR, Ubuntu 22.04/24.04, Python 3.12, system XCB/OpenGL/Xvfb packages, pinned dev install + editable app, pip check, full Xvfb/Mesa pytest.
- No workflow release build/export, noneditable wheel install, JUnit/coverage upload, screenshot/log artifact upload, explicit job timeout, explicit workflow permissions, or stale-run concurrency cancellation in this file. This is a repository-config observation, not a statement about inaccessible GitHub organization policy.
- `requirements-dev.lock` pins transitive versions but lacks hashes; setuptools build requirement `>=75` floats. Existing source install path is documented in `README.md:232–247`; no frozen Linux binary release pipeline was found.
- `DEPENDENCIES.md:24` explicitly defers binary distribution compliance audit; source distribution and separate replaceable shared dependencies are intended. Treat license/bundling checks as a real prerequisite if distributing frozen builds, not a reason to introduce packaging now without product need.

### Docs and agent conventions

`AGENTS.md:3–13` is unusually useful: offline Linux mechanical CAD, parameter/widget separation, B-rep authority, explicit units, finite dimensions, build-before-commit, no speculative plugin framework, meaningful geometry/render checks, documented limits, branch/PR/no auto-merge. README, dependency rationale, validation history, feature-specific manual guides, audit/performance docs and benchmark JSONs are substantial strengths.

Documentation is append-heavy and can mislead new agents: early `ARCHITECTURE.md:26,36,48,56` says persistent naming out of scope, hides solids in sketch mode, describes V3 and says booleans/extrusion future; current code and later sections implement more. `VALIDATION.md` contains historical 950-pass records, not fresh evidence by itself. `pyproject` remains version 0.0.12 through many feature work orders. Recommendation: compact current-state index linking historical notes; do not delete historical evidence.

### Risks (inferences grounded in inspected code)

1. Topological reference stability after edits remains inherently complex: attachment/lineage resolution, chamfer identity and ambiguous regions need retained regression corpus with explicit unresolved states. Current restrictive behavior is safer than silently selecting a different region; broadening requires independent geometry oracles.
2. Ordered synchronous regeneration and pairwise region/line checks (`profiles.py:73–92`, `line_profiles.py:55–87`) can become slow even below allowed limits. Existing benchmark scripts should be reused; avoid speculative async rewrite.
3. Native UI/render behavior varies by GPU/Wayland/HiDPI. Xvfb/Mesa success cannot establish NVIDIA laptop selection feel or native dialogs. Preserve human CAD acceptance for visible geometric correctness, selection, dimensions, sketch/extrusion/chamfer workflow.
4. Main window is 1663 lines and viewport 730 lines, while document is 615. Size is not proof of poor design, but edit/display publication and selection coupling are review hotspots. Extract only when a concrete change benefits, with transaction invariants preserved.
5. Packaging currently validates editable source installs. An installed-wheel smoke is a small useful follow-up; a frozen installer is a separate decision with dependency-license maintenance cost.

### Prioritized recommendations

| Recommendation | Benefit | Complexity / ongoing cost | Dependencies | Risks | Human approval |
|---|---|---|---|---|---|
| Preserve existing two-OS suite; add concise test evidence/artifacts and bounded CI timeout/concurrency | Less human log chasing and hung runs | Low / low | Existing Actions | Artifact privacy, mistaken cancellation scope | Follow-up WO authorization; routine details delegated; merge remains human |
| Maintain failure-based geometry corpus and commit-pinned replay commands | Prevent recurring topology/save/regeneration defects | Medium / medium per new feature | Existing tests and fixtures | Self-confirming oracle | Follow-up authorization; product semantics changes require human |
| Noneditable wheel install/import/entrypoint smoke | Detect packaging omissions | Low–medium / low | Current setuptools + pinned environment | Does not prove desktop rendering | Follow-up authorization; no frozen package implicitly authorized |
| Current architecture index with current schemas and known unsupported profiles | Lower agent confusion and repeated human explanations | Low / low | Existing code/docs | Stale index if unmaintained | Follow-up authorization; docs-only merge human |
| Retain focused physical CAD acceptance once per consolidated PR | Catch feel/selection/graphics and unexpected geometry | Low implementation / modest human time | Green applicable automated gates | Manual geometry review is not exhaustive | Human acceptance explicitly required |

Do not add Nexus dependencies, telemetry, accounts or mandatory network services to HERO-CAD. Any optional future agent interface must preserve ordinary offline modeling; current WO does not authorize that feature.

Source browser pinned to this audit: https://github.com/TAM-Hiding/hero-cad/tree/56983d35ae255365462361baeb89cdc851ac32b4


## Requisition Denied audit evidence — WO-001

Audit date: 2026-11-17. Verified default ref: `refs/remotes/origin/main`; pinned commit `a362667fa7ce8942c234e56e3936cd42ed89e384` (RD-009 merge). This is the default branch, not the unmerged RD-010 Wayfarer work. Source clone remained clean. Findings below are static inspection unless explicitly described as executed. No application source changed.

### Architecture and existing strengths

- Godot/GDScript standalone Linux-first game. `project.godot:13` starts `scenes/facility.tscn`; `project.godot:135` selects Jolt; `project.godot:139` selects GL Compatibility. README:3 specifies Godot 4.7.2; `tests/validate_project_configuration.gd:13` enforces exact 4.7.2. No third-party addon dependency is tracked. Python standard library is used by the editor-cycle harness; Bash wraps tests. Engine binary and matching export templates are external dependencies, not a reproducible pinned installer in this tree.
- World definitions (`scripts/world/object_definition.gd`) are distinct from live bodies (`interactable_object.gd:3–24`). Per-actor observation snapshots are deep-copied in `scripts/knowledge/player_knowledge.gd:3–23`, preserving learned versus current world state. `scripts/actions/interaction_service.gd:3–42` gates reach, sight and available actions outside UI; some actions intentionally require OtisController.
- Player locomotion, equipment, held presentation, precision placement and collision clearance are separate modules. Runtime object states WORLD/HELD/STOWED/MOVING/CARRIED are explicit (`interactable_object.gd:4`); placement also owns grab/seating/support/input state (`precision_placement.gd:19–48`). Mechanical mount access dependencies and fixed-joint compatibility are explicit (`mechanical_mount.gd:13–38`). Revolute/prismatic metadata does not imply simulated joints: line 32 rejects non-fixed kinds.
- Signals/load sensors/barriers, terminal administration, mechanical components/mounts, fastening graph/ram and scrap stock have separate directories. `scripts/world/facility.gd:23–87` composes the scene procedurally, connects interfaces, and builds geometry. Chassis seed can be set before insertion (`facility.gd:20–24`); tests use fixed seeds.
- Fastening graph rebuild restores original bodies, collisions, freeze state and velocities (`fastening_system.gd:576–627`). This provides a useful future persistence seam but no world save serializer exists in inspected source. Settings alone persist through schema validation and temporary-file rename (`mechanical_interaction_settings.gd:65–105,111–125`). README:41 and :239 explicitly describe session-local knowledge and fastening/ammunition. Persistent world/clone/exit-save mechanics are future product work, not existing features to claim tested.

### Tests, coverage, automation and documentation

- `tests/validate.sh:1–29` is an existing reusable engine integration runner: import, thirteen GDScript validation scripts, then startup `--quit-after 120`. It uses pipefail and scans ERROR/SCRIPT ERROR diagnostics, addressing Godot zero-exit-on-error behavior. No addon test framework is required. There is no source line/branch coverage report; assertion counts are behavioral checks, not coverage percentages.
- Suites cover facility/knowledge/action permissions, mobility, manipulation, equipment poses, configuration, environmental logic, precision placement, terminal, physics, seeded chassis, mechanical assembly, universal fastening, scrap stock. Mechanical and fastening suites are extensive (583 and 982 lines), with explicit regressions for concurrent tool/grab use, topology splits, invalidated edges, ram recalculation and collision. Tests often invoke domain methods directly; graphical input ownership remains separately exercised (`validate_mechanical_assembly.gd:140–147`).
- Screenshot capture already exists via RD_SCREENSHOT in several scripts (e.g. `validate_equipment_poses.gd:103–111`). No approved image baselines, pixel/perceptual comparisons or drift thresholds were found; image capture is not a screenshot regression gate.
- `tests/validate_editor_configuration.py:16–65` copies the project, injects a disposable editor plugin, runs the real editor, checks settings bytes and clean git state. It requires graphical Linux and is not invoked by validate.sh. Historical documented passes (`docs/rd-002-final-polish.md:33–78`) are claims from earlier work, not this audit's executed results.
- Tracked-file inventory (134 files) has no `.github` workflows, `export_presets.cfg`, packaging script, AGENTS.md or PR template. This verifies absence of in-repository CI/build automation; external account-side automation is not established by this inspection. `.gitignore:4–6` excludes builds/exports but does not provide a build workflow.
- README:255–313 gives architecture, local run/test commands and headless/graphical distinction. Historical RD-001/002/003 docs offer manual walkthroughs and known limitations. README introduction still foregrounds RD-002 although body and main include RD-009: documentation is useful but version framing is stale. No single enforceable agent policy, check manifest, evidence format or run budget is tracked.

### Executed baseline and limitations

Installed `/usr/local/bin/godot --version` returned `4.6.3.stable.official.7d41c59c4`, not required 4.7.2. Tests were run from a disposable `git archive HEAD` extraction with XDG_DATA_HOME and XDG_CONFIG_HOME redirected under `/workspace/scratch/727ab565ddbc/rd-baseline`, protecting user settings and the source tree.

Executed command:

```sh
XDG_DATA_HOME=/workspace/scratch/727ab565ddbc/rd-baseline/data XDG_CONFIG_HOME=/workspace/scratch/727ab565ddbc/rd-baseline/config GODOT_BIN=/usr/local/bin/godot bash /workspace/scratch/727ab565ddbc/rd-baseline/project/tests/validate.sh
```

Result: exit 1. Import completed without error diagnostics; facility 61/0, mobility 56/0, manipulation-followup 42/0 and equipment poses 38/0 checks/failures. Configuration 16 checks, 2 failures: exact engine version and byte-identical canonical project serialization. These failures under an unsupported engine do not establish a target-engine application defect. Wrapper stopped there. No full supported-version pass is claimed.

Additional compatibility-only scripts were executed individually with the same isolated XDG directories, each with 60-second subprocess timeout; results appended below. Graphical editor cycle, graphical pointer checks, target-version tests and exported Linux build were not run. No numerical code coverage was measured.

### Risks and recommended follow-ups (proposals, not changes)

| Recommendation | Benefit | Complexity / maintenance | Dependencies | Risk | Approval |
| --- | --- | --- | --- | --- | --- |
| Add Linux CI invoking the existing wrapper with verified 4.7.2 binary/checksum, isolated XDG directories, timeouts and retained logs | Catches regressions before human testing without replacing good existing tests | Low–medium; maintain engine pin and action pins | Confirm obtainable exact engine and runner | Wrong version produces false failures; shared XDG leaks preferences | Separate implementation WO and normal merge approval; security approval for any privileged runner/secrets |
| Add Linux export preset and matching template provisioning, smoke exported artifact | Gives product owner one repeatable build per accepted candidate | Medium; release tooling upkeep | Supported engine baseline | Export-only missing resources, driver assumptions | Scope authorization and final merge; no public release without approval |
| Add state invariant checks and seeded multi-step sequences around ownership transitions/topology | Finds combinations beyond fixed historical regressions | Medium; bounded seed corpus/tolerances | Existing tests and deterministic fixture control | Flaky timing if exact transforms are overasserted | Routine technical detail within a test WO; merge approval |
| Add small graphical regression job with approved stable camera scenes and tolerances | Detects visible regressions headless cannot see | Medium ongoing rendering baseline upkeep | Reliable software/GPU renderer and candidate artifacts | Image noise or misleading automatic visual acceptance | Product owner approves baseline/design; merge approval |
| Keep focused human playtest for pickup/retraction, seating, fastening failure/split, ADS/tool sight, collision feel and terminal input | Protects interaction feel and product intent | Low–medium recurring human time | Consolidated tested candidate | Automated pass cannot establish usability | Human acceptance required |
| Define persistence identity/save contract only in its own product WO | Prevents introducing accidental save semantics or losing object graph identity | Medium–high later; schema/version upkeep | Human-defined exit/death/reload policy and stable object/connection IDs | Serialization timing, physics restoration, duplicates | Explicit product approval before persistence implementation |

Architectural concern: facility builder (643 lines), interaction UI (517), precision placement (525) and fastening system (730) concentrate responsibilities. Their size alone does not justify rewriting. Protect boundaries with tests and extract only when a concrete change needs it. Body ownership restoration and overlapping state flags are the higher-value regression targets. Physics behavior is engine/backend/timing dependent, and method-level checks leave input/visual gaps. Recommend stronger current runner evidence before any orchestration infrastructure.

### Supplemental executed compatibility results (Godot 4.6.3)

Each command used `/usr/local/bin/godot --headless --path /workspace/scratch/727ab565ddbc/rd-baseline/project --script tests/validate_NAME.gd`, with the same isolated XDG environment as above and a 60-second Python subprocess timeout. All completed before timeout.

| NAME | Checks | Failures | Exit | Error diagnostics |
| --- | ---: | ---: | ---: | --- |
| environment | 37 | 0 | 0 | None |
| precision_placement | 55 | 0 | 0 | None |
| terminal | 34 | 0 | 0 | None |
| physics_followup | 47 | 0 | 0 | None |
| android_chassis | 82 | 0 | 0 | None |
| mechanical_assembly | 162 | 0 | 0 | None |
| universal_fastening | 392 | 0 | 0 | None |
| scrap_stock | 164 | 1 | 1 | `V changes grade and HUD` |

Separate startup command `/usr/local/bin/godot --headless --path /workspace/scratch/727ab565ddbc/rd-baseline/project --quit-after 120` exited 0 without error diagnostics (30-second timeout). The scrap-stock failure is unresolved: reproduce on supported 4.7.2 before deciding whether it is an application regression, test issue or version-dependent behavior. It must not be dismissed as definitely caused by the engine mismatch. No corrective source edits or repeated speculative retries were performed.

Evidence logs are retained temporarily at `rd-baseline/validate.log`, eight named suite logs, `rd-baseline/remaining-results.json` and `rd-baseline/startup.log`. Aggregate observation across the wrapper prefix and separate runs: eleven GDScript scripts passed on 4.6.3, configuration and scrap-stock scripts failed. This is not a successful execution of the complete supported-version wrapper. Original repository `git status --short` remained empty after validation.

Source browser pinned to this audit: https://github.com/TAM-Hiding/requisition-denied/tree/a362667fa7ce8942c234e56e3936cd42ed89e384


## Unresolved evidence and acceptance needs

- No actual Archive user corpus was available; source fidelity for representative private documents, scale, backups and restore must be tested locally using copies. CI fixtures must remain permission-safe.
- No claim of Archive authorization safety, concurrent-writer correctness or complete ingestion coverage follows from 185 passing tests.
- CAD GUI, native graphics, clean noneditable distribution and user interaction remain unverified in this environment. Current CI is strong evidence but not a replacement for physical modeling acceptance.
- RD requires a verified 4.7.2 runtime/templates supply before its supported baseline can be established. Reproduce the scrap-grade failure there; do not weaken version or HUD assertions to make CI green.
- No persistent Nexus deployment, API credential availability or unrestricted background agent execution was established.
- Temporary log paths record where commands ran; they are not permanent artifact links. The durable audit records commands, versions, counts, limitations and observed failures here. Re-run at a fresh pinned SHA before implementing follow-ups.
