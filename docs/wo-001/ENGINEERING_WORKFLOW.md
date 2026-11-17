# TAM engineering workflow — WO-001

Status: proposed standard; documentation only. Audit date: 2026-11-17.
Companion documents: [audit](REPOSITORY_AUDIT.md), [Archive evolution](ARCHIVE_EVOLUTION.md), [orchestration](AGENT_ORCHESTRATION.md), [roadmap](IMPLEMENTATION_ROADMAP.md).

## Decision

Adopt a bounded implement–test–correct–review loop on one branch, followed by one consolidated human acceptance handoff. Start with existing repository tooling and GitHub PRs. TAM Nexus is not a prerequisite. Human curiosity is encouraged, but understanding implementation internals must not become a prerequisite for engineering progress.

## Authority

| Role | Decides and performs | Boundary |
|---|---|---|
| Human product owner | Goals, behavior, UX/visual design, priorities, consequential scope, security/privacy policy, destructive operations, acceptance and merge | Technical comprehension is not a required approval gate |
| Technical architect | Architecture, contracts, engineering choices, acceptance criteria, significant tradeoff assessment | Explain consequential product effects; do not redefine product intent |
| Implementer | Inspect, plan, reversible technical choices, code, tests, diagnosis, documentation, bounded corrections | No implicit authorization to weaken security, delete user content or merge |
| Separate reviewer | Read requirements and final diff, inspect tests, attempt targeted falsification, report severity/evidence | Must be a separate agent/person; same-agent second pass is self-review |

Routine engineering decisions within an authorized work order do not require repeated permission. A future work order must still authorize its implementation: this audit authorizes none of the roadmap changes. Every merge needs explicit human approval. Existing repository instructions remain applicable; resolve genuine conflicts against the work order before changing scope.

Archive architecture can be primarily architect-led. HERO-CAD retains focused owner involvement in CAD behavior and interaction. Requisition Denied retains frequent design/playtest involvement for game feel. These differences affect acceptance checkpoints, not the obligation to run available automated checks.

## Lifecycle and exit evidence

| Stage | Required action | Exit evidence |
|---|---|---|
| A Specification | State observable behavior, constraints, exclusions, acceptance examples, affected repositories, risk class and budget | Work order; ambiguity register distinguishes blocking product decisions from routine engineering choices |
| B Baseline | Read AGENTS and current docs; resolve default branch and SHA; inspect dirty work; create isolated branch/worktree; inspect test side effects; run available baseline | SHA, environment, exact commands, counts, failures/skips, exit codes and limitations; no use of personal live data |
| C Implementation | Smallest coherent change; preserve contracts and user content; add behavior-oriented regressions when warranted | Reviewable diff; no unrelated cleanups or generated noise |
| D Verification | Relevant unit/integration/regression tests, clean build/install/startup and project checks; inspect actual assertions and logs | Results tied to exact candidate SHA, not an earlier successful commit |
| E Correction | Classify failure as introduced, baseline, infrastructure or unresolved; reproduce, correct and rerun affected checks | Bounded attempt ledger and updated evidence |
| F Review | Separate reviewer gets specification, baseline, diff and evidence; review correctness, regressions, security and maintenance | Reviewer identity/type, reviewed SHA, findings, dispositions; if unavailable, explicitly record self-review only |
| G Human acceptance | Consolidated draft PR, artifacts where useful and short reproducible acceptance script | Owner tests product-level outcome and approves/rejects; no automatic merge |

A baseline failure does not authorize unrelated repairs or disguising a red suite. Isolate the failure and describe its relevance. A known unrelated failure may accompany a draft PR but cannot be advertised as fully green. Environmental failure is not application failure or success. A timeout, skipped test, import-only smoke or process exit without assertions is not equivalent to behavioral verification.

### Default bounds

For a small work order, permit up to three corrective iterations and two independent review rounds, with a default 90-minute execution budget unless the work order supplies another limit. These are operating defaults to tune from measured results, not guarantees of session duration. Stop earlier on repeated identical failure without new evidence, exhausted resources, unavailable prerequisites, unresolved data risk or required scope expansion. Report remaining work and the next reproducible command; never silently extend the budget or relax a test to pass.

After a correction, rerun affected checks and the required suite once. Re-review changed portions that affect prior conclusions. No ritual full reruns after documentation-only changes unless CI policy requires them. New changes or new evidence justify additional testing. No tests that merely reproduce implementation internals or assert prose formatting.

## Evidence contract

Record repository, base SHA, candidate SHA, OS/runtime/dependency versions, command, working directory, isolated data path, start/end, exit status, pass/fail/skip counts, log/artifact references and known limits. Label each conclusion:

- **Verified—executed:** command succeeded/failed in this run, with scope.
- **Verified—static:** source/configuration inspected at pinned SHA.
- **Observed—remote:** GitHub run/check reports a result; not locally reproduced.
- **Proposed:** recommendation or intended future behavior.
- **Unresolved:** not assessed, blocked or unsupported.

Measure statement/branch coverage only with the tool, include scope and exclusions, and never translate counts of tests into a coverage percentage. Coverage indicates exercised code, not correctness. Prefer assertions against invariants, observable state and preservation of user data.

## Project verification contracts

| Project | Proposed automated target (introduced incrementally) | Human acceptance retained |
|---|---|---|
| Archive | Synthetic-source ingestion; source byte/hash preservation; viewer-page vs printed-page citations; metadata/ID stability; retrieval ranking fixtures; large-document bounds; migration dry-run/restore; conflicting writes; denied reads/writes/search/previews | Source-context usefulness, curation UX, representative private corpus checked locally |
| HERO-CAD | OCCT validity/bounds/mass properties; regeneration after upstream edits; feature-history IDs/dependencies; `.hcad` round trips; sketch/region identity; real document changes in UI tests; clean Linux install/startup; defect regressions | Selection/snaps, interaction feel, model intent and geometric correctness with representative parts; automated checks remain complementary |
| Requisition Denied | Pinned Godot import and headless script harness; scene/resource load; deterministic interaction assertions; physics transitions with tolerances; eventual persistence/reload semantics; Linux export and startup; controlled scene/image comparisons | Visual quality, hand/tool orientation, manipulation, emergent physics and gameplay feel; planned intermediate playtests at design milestones |

Do not make unimplemented features mandatory passing gates: Archive migrations and RD saves need tests when their implementation is authorized. Tests should expose existing defects before fixing them, but new CI baselines must explicitly classify known failures rather than conceal them.

## Handoff template

```markdown
Problem and resulting behavior:
Scope and explicit exclusions:
Base / candidate SHA:
Significant decisions and product implications:
Baseline commands and results:
Final commands and results (including failures/skips):
Independent review identity, SHA, findings and disposition:
Artifacts and environment:
Remaining limitations / risks:
Human acceptance: prerequisites, steps, expected outcome, stop conditions:
Rollback/recovery:
Merge: awaiting human approval; auto-merge disabled/not requested.
```

Keep the PR description current with the final implementation, not the conversation history. Acceptance evidence and review must identify the commit being accepted. If the base changes, inspect the integration diff and rerun affected gates before merge approval is used. Human acceptance rejection becomes a scoped correction on the same PR unless it changes product intent enough to require a new work order.

## Recommendation ledger

Complexity/maintenance are qualitative: low = small repository change, medium = multiple components/platform concerns, high = ongoing distributed/security responsibility. All costs exclude unknown corpus/hardware variability.

| ID | Recommendation / benefit | Complexity / maintenance | Dependencies | Risk | Human approval |
|---|---|---|---|---|---|
| W1 | Standard work-order and evidence/PR template; reduces repeated coordination | Low / low | Owner adopts standard | Checklist substituted for actual evidence | Adoption and merges; no per-detail approval |
| W2 | Baseline plus bounded corrective loop; catches defects before handoff | Low / low | Runnable tests and isolated data | Baseline failures hidden by retries | Authorized work order suffices; expansion requires approval |
| W3 | Separate reviewer for consequential changes; reduces correlated blind spots | Low–medium / low | Separate execution context | Shared model assumptions remain; not a security certification | Within authorized verification; merge stays human |
| W4 | Project-specific automation plus focused human acceptance | Medium / medium | Roadmap gates and representative fixtures | Headless success misses UX/physics/render problems | Feature/UX decisions and merges |
| W5 | Evidence tied to SHA with resumable checkpoint | Low / low | Git/PR access | Stale evidence after new commits | Routine within work order |

WO-001 does not enforce branch protection, install an agent service or alter repository settings.
