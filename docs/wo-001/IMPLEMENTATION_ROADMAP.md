# Implementation roadmap — TAM WO-001

Status: prioritized proposals only; none implemented by this audit. 2026-11-17.
Read [verified findings](REPOSITORY_AUDIT.md) and [workflow](ENGINEERING_WORKFLOW.md) first.

## Sequencing and approval

Start with small repository-local improvements and demonstrated defects. Work may proceed independently across repositories after the owner authorizes the relevant work order; no need for a Nexus deployment. Each row is a separately reviewable PR/work order. All require human merge approval. “WO” means authorize that follow-up's scope, not reapprove every technical choice. Security/privacy policy, destructive migration, product semantics and new infrastructure require explicit approval as identified below.

| Priority / WO | Deliverable and independently testable exit | Benefit | Complexity / maintenance | Dependencies | Risks | Approval |
|---|---|---|---|---|---|---|
| P0 / WO-002 | Archive reproducible baseline + Linux CI + contributor/test handoff instructions; clean install, pip check, existing suite and artifact evidence | Immediate reduction in human test relay | Low–medium / low | Existing pytest suite; network/package availability | Dependency drift, passing suite mistaken for exhaustive safety | WO and merge; no secrets/settings changes |
| P0 / WO-003 | Archive authored-note integrity: stable IDs/unknown metadata survive edit; path containment; collision rejection; regression tests | Protect content and references | Low–medium / low | WO-002; legacy fixture inventory | Legacy metadata/path compatibility, collision UX | WO with collision behavior specified; merge; no bulk repair |
| P0 / WO-004 | Archive safe HTML highlighting + documented loopback/no-debug launch and mutation protections | Addresses observed raw-content rendering risk before shared access | Low–medium / low | Rendering/route fixtures; can follow WO-002 independently | Escaping regressions, local launch compatibility | WO/merge; no network exposure; new policy owner decides |
| P1 / WO-005 | RD supported-engine baseline and Linux CI using existing wrapper, XDG isolation, timeouts and logs; classify scrap failure on 4.7.2 | Routine detection of gameplay regressions | Medium / low | Obtain and verify required engine; no assertions weakened | Unavailable engine or reproducible baseline failure | WO/merge; blocked report if runtime unavailable |
| P1 / WO-006 | CAD CI evidence/time bounds, clean noneditable wheel smoke and current-state documentation index | Catch distribution omissions; reduce agent confusion | Low–medium / low | Existing CI/locks; obey AGENTS | GUI driver differences, misleading historical docs | WO/merge; no frozen distribution implied |
| P1 / WO-007 | Archive root/service abstraction and atomic/revision-safe note/metadata writes; conflict and failure-injection tests | Consistent reusable service seam | Medium / medium | WO-003/004 | Changes to legacy path resolution | WO/merge; no content relocation |
| P1 / WO-008 | Archive source hashes/revisions and stable citation contract; additive readers and legacy mapping report | Durable evidence for agent queries | Medium / medium | WO-007 | Ambiguous old references | WO/merge; actual repair/migration separately approved |
| P1 / WO-009 | Archive recoverable derived generations and backup/restore drill on synthetic copies | Avoid partial multi-file updates | Medium / medium | WO-007/008 | Partial generation publication | WO/merge; live cutover/destructive steps require approval |
| P2 / WO-010 | Archive retrieval/large-PDF characterization, then only justified bounded processing/index improvement | Establish completeness and scale limits | Medium / medium | WO-008/009; representative synthetic corpus | Benchmark optimizations regress relevance | WO/merge; staged implementation after measurement |
| P2 / WO-011 | Archive versioned read API + contract tests for refs, warnings, pagination and revisions | Independent service access | Medium / medium | WO-008/010 | Exposed paths, stale refs | WO/merge; remain local until WO-013 |
| P2 / WO-012 | Assertion/verification/applicability data + minimal human UI with owner-approved semantics | Separate confidence from evidence | Medium / medium | WO-008; product semantics | False authority, cumbersome curation | Product/UX approval, WO and merge |
| P2 / WO-013 | Archive authorization policy and negative tests across search/files/previews/cache; read-only agent pilot | Safe personal/shop separation | Medium–high / medium | WO-011; approved identities/data policy | Information leakage | Explicit security/privacy/deployment approval and merge |
| P2 / WO-014 | RD Linux export preset/templates and artifact smoke; focused acceptance packet | One repeatable candidate build | Medium / medium | WO-005; runtime/template provenance | Export omissions, graphics differences | WO/merge; no public release without approval |
| P2 / WO-015 | RD seeded multi-step state regressions and controlled graphical baseline pilot | Catch interaction combinations and visible regressions | Medium / medium | WO-005/014; reliable renderer | Flaky physics/image thresholds | Owner approves visual baseline; WO/merge |
| P2 / WO-016 | CAD defect-replay corpus and measured regeneration cases | Protect topology/history without speculative rewrite | Medium / medium per feature | WO-006; representative failures | Self-confirming numerical oracle | WO/merge; modeling behavior owner decides |
| P3 / WO-017 | Minimal Nexus registry + CSI schema/read-only Archive and GitHub references for one demonstrated task | Cross-project context reuse without duplicate stores | Medium / low–medium | WO-011/013; second consumer or measured need | Premature infrastructure, cross-project leaks | New infrastructure and policy approval; merge |
| P3 / WO-018 | Durable run checkpoint/executor adapter, then bounded CI-correction pilot if justified | Recover interrupted jobs and reduce repeat supervision | High / high | WO-017; budget/host/backend/credentials | Runaway jobs, untrusted inputs, spend | Explicit security/spend/host approval; merge |
| Product-gated / WO-019 | RD save/persistence contract and identity fixtures before implementation | Preserve intended exit/death/clone semantics | Medium–high / medium | Owner-defined product behavior; existing state graph | Accidental save mechanics, broken graph reload | Explicit product approval; separate implementation WO and merge |

P0 defects must not wait behind P2/P3 infrastructure. If CI setup is externally blocked, an authorized WO-003/004 may use the recorded local baseline and proceed without waiting for hosted automation. Preserve those blockers in PR evidence. Do not add failing regression cases to the required baseline without a scoped correction or an explicit red-baseline report; do not hide failures through skip/xfail to claim success.

## WO-002 — Archive reproducible verification baseline

### Objective and scope

Repository: `TAM-Hiding/archive-v0`. Starting reference for planning: `main` at `efb3b06419b815b40e8fc24e68f6afe5c0fcfd5b`; resolve and record the actual current default SHA at execution, read any new AGENTS instructions and account for intervening changes. Create a dedicated branch and draft PR; do not merge automatically. This is ready to issue independently after authorization.

Make the existing Archive test suite reproducible on a clean Linux environment and runnable in ordinary GitHub PR/push checks. No application behavior changes, source refactor, ingestion migration, new agent service or fixes for WO-003/004 are included.

### Authorized change surface

- Dependency input/constraint or lock files and documented regeneration command. Preserve runtime dependencies and their roles; separate development tools without gratuitous upgrades. Use Python 3.12 as the initial **proposed tested baseline**, not a claim that the app already declares that support policy. Audit used 3.12.14 and Flask 3.1.3/pdfplumber 0.11.10/pypdf 7.1.0/pytest 9.2.0; re-resolve and validate pins rather than copying an unverified environment.
- `.github/workflows/tests.yml`, a small local verification entrypoint if it avoids duplicated commands, `AGENTS.md`, README testing section, and PR evidence template. No changes to `app.py`, `archive.py`, `ingestion/`, templates or maintenance application logic.
- Test configuration only if necessary to produce reports/isolate paths; no altered assertions, skips or xfails. Existing test code should ordinarily remain unchanged. Record any need to expand this boundary rather than doing so silently.

### Implementation contract

1. Inspect tests for live-data side effects and run the baseline from a clean checkout with empty/disposable data. Use a fresh venv. Record full test count and versions; WO-001's 185-pass count is historical, not a fixed future count.
2. Select a maintainable lock/constraints approach compatible with pip and Linux. Include transitive versions and explain how to refresh/verify them. Prefer existing tools; avoid a new package manager solely for this task. Runtime installs should not require pytest; development installation includes pytest and coverage tooling if coverage output is added.
3. Local recipe: create venv, install pinned development dependencies, `python -m pip check`, `python -m pytest -q` with JUnit output. If coverage is added, measure source directories/files explicitly, identify never-imported modules and enable branch coverage only with a clear report; set no arbitrary percentage gate in this WO.
4. CI: Ubuntu 24.04, Python 3.12, `push` on main and `pull_request`, read-only contents permission, no secrets, immutable reviewed action SHAs, 15-minute job timeout and per-PR/ref concurrency cancellation. Use a temporary working/data environment. Cache only dependencies keyed by Python/lock, never user documents.
5. Upload test/JUnit and dependency diagnostics on failure as well as success, with a short documented retention (initial proposal: 14 days). Upload only synthetic-test output; no personal source corpus, local home directory or credentials. Avoid a pipeline where artifact upload hides the test exit code.
6. Document the same local/CI command and contributor policy: preserve sources/authored metadata, no live-data tests, bounded correction, honest evidence, branch/PR workflow and no automatic merge. Reference this standard without copying all audit findings into AGENTS.

### Acceptance criteria

- A fresh venv can install using the documented pinned files; `pip check` exits zero.
- All existing tests pass from a clean checkout, with counts and skips recorded. If a baseline failure occurs, diagnose and report; only environment/verification setup corrections are within scope.
- A second clean install using the same lock resolves the same package versions; no unexpected repository/data changes remain after test execution.
- On the candidate PR SHA, GitHub Actions actually runs the suite and exposes readable results/artifacts. If Actions execution or artifact retrieval is unavailable, leave draft with explicit limitation; do not declare this criterion satisfied from YAML inspection.
- CI failure propagation is demonstrated with a temporary nonzero command in a disposable local test of the wrapper, or an isolated throwaway workflow run if practical; do not commit a broken test or alter application assertions. Check artifact collection cannot turn the failed job green.
- The final diff is confined to the authorized infrastructure/documentation surface. No application source, repository settings, secrets or real data changed.
- Separate reviewer checks dependency reproducibility, workflow permissions/event safety, meaningful test execution and evidence accuracy. Maximum three corrective iterations/two review rounds and 90-minute default active budget; stop with a checkpoint on external blockers.

### Human acceptance and rollback

Human acceptance is one short verification: inspect the consolidated PR, confirm the Actions run/artifacts match its head SHA, and optionally run the documented local command on a disposable checkout. No PDF content migration or GUI feature testing is required for this infrastructure-only WO. Owner approves merge explicitly. Rollback is reverting the infrastructure/documentation commit; dependency changes remain confined to venvs, and no data restoration should be necessary.

### Expected outcome and next handoff

The coding agent returns the PR, exact commands/results, dependency versions, independent review outcome, limitations and any remaining approval-relevant choices. The architect then prepares WO-003 with concrete metadata-preservation/path/collision acceptance cases. Do not begin that fix or any other roadmap item as part of WO-002.

## Progress evaluation

After the first several authorized PRs, compare human acceptance cycles, owner debugging time, defects caught before handoff, flaky failures and agent/review time. Keep the workflow if coordination falls without masking defects. Only then decide whether a persistent Nexus scheduler adds enough value to justify its maintenance and security cost.
