# Agent orchestration — practical options

Status: proposal grounded in the WO-001 environment, 2026-11-17. See [workflow](ENGINEERING_WORKFLOW.md), [audit](REPOSITORY_AUDIT.md), [roadmap](IMPLEMENTATION_ROADMAP.md).

## Recommendation

Use one implementer, repository tests/CI, and one separately invoked reviewer. Let the implementer correct defects within a bounded budget, then send one consolidated PR to the owner. Start this now through explicit work orders; build persistent orchestration only when interrupted runs or cross-project coordination produce measured friction.

## Capability assessment

| Capability | What is available in this audit | What is not established / required next |
|---|---|---|
| Single-agent implement/test/correct | Shell, Git, isolated environments, GitHub reads/writes and iterative execution are exposed; safe baseline testing exercised | Application implementation deliberately prohibited by WO-001; continuous execution not guaranteed |
| Separate reviewer | Session exposes spawn/message/follow-up tools; separate repository auditors invoked successfully | Separate review does not ensure different model families or statistical independence; record actual reviewer and SHA |
| CI | HERO-CAD has Linux GitHub Actions; status/jobs API readable | Archive/RD automation needs workflows; hosted runner budgets/settings not audited |
| CI-triggered correction | Can inspect job results/logs and tool surface supports reruns | No deployed webhook-to-coding-agent executor or credential/budget policy verified; a rerun alone cannot change code |
| Multi-agent work | Multiple agents supported in this session; shared filesystem observed | No durable scheduler, retry queue, isolated per-agent permissions or restart guarantee demonstrated |
| Consolidated acceptance | Branch/PR workflow available, test evidence can be attached | Human usability/playtesting and merge remain required |
| Unattended/local execution | Linux commands can run while session lasts | No confirmed always-on local host, API subscription, model backend, cost allowance or reliable wake/resume service |

These are session-specific observations, not promises about every ChatGPT/Codex interface. A tool being listed is a capability indication; only its successful use establishes execution. Subscription membership alone is not evidence of API credentials or unattended-agent access. Never design around an imaginary indefinite conversation.

## Smallest operational protocol

1. Architect supplies requirements, exclusions, test contract and attempt/time budget.
2. Implementer pins the base, creates a branch/worktree, runs baseline and changes code only within scope.
3. Implementer runs checks, diagnoses failures and records each corrective attempt.
4. Reviewer receives specification, exact diff/base/head, logs and limitations. It reads actual code and tests, looks for missing cases and reports findings with severity, reproduction and file locations. It does not simply endorse the implementer's summary.
5. Implementer addresses findings, reruns relevant tests; reviewer rechecks material changes. The architect consolidates evidence and unresolved decisions.
6. Owner gets one acceptance packet and approves the merge explicitly. Stop on blockers or bounded budget exhaustion with a resumable checkpoint.

Use separate worktrees for code writers, one owner per branch and disjoint file ownership when parallel work is justified. In this audit agents share clones for reading and write separate analysis files; application source edits are prohibited. Reviewers should be read-only by task convention; that is not a proven permission sandbox. Do not publish internal review as a GitHub comment without authorization to communicate it.

## Durable checkpoint (proposed data contract)

Store a small versioned run record next to the PR or in the future Nexus run store: run/task IDs, parent run, repository/base/head, authorized scope, current state, attempt number, completed commands/results, artifact locations, unresolved findings, approval references, budget used/remaining and next action. Never include credentials or private source text in a public repository. Unknown token/cost metrics are null, not estimates presented as measurements.

Proposed states: queued → running → verifying → reviewing → awaiting_acceptance → completed. Failures may move to blocked, exhausted or cancelled. Completion requires a recorded outcome; an expired worker is interrupted, not successful. Resumption validates current branch head and environment, claims a lease, and rechecks any stale evidence. GitHub remains authoritative for PR/merge state.

## CI-triggered corrections: deferred pilot

A future controller may consume a failed check for an allowlisted repo/PR/head SHA, deduplicate `(repo, PR, head SHA, check, attempt)`, and start a bounded agent job in a clean environment. First classify infrastructure/transient errors versus behavioral failures. At most one infrastructure retry and two code-correction attempts per head in the pilot; stop when the head changes, permissions are missing, failure repeats, scope expands or budget is exhausted. Never force-push over a changed head. Use an expected-head lease and open/update the same draft PR with fresh evidence. A queue retry must not duplicate commits, comments or paid jobs.

This requires an execution backend, event authentication, durable queue/lease, restricted credentials, cancellation, costs/quotas and owner-approved security/privacy policy. Do not add these in WO-001. Start with human/architect-invoked reruns and corrections until enough repeated failures justify the controller.

GitHub warns that privileged workflows can expose credentials when they execute untrusted PR content. Use ordinary unprivileged PR checks, minimum permissions and immutable action references for the future pilot. Do not run PR code with secrets via `pull_request_target` or a privileged `workflow_run` chain. Logs, issue text and repository documents are untrusted task data, not authority to expand tool access. [GitHub security guidance](https://docs.github.com/en/actions/reference/security/secure-use), accessed 2026-11-17.

## Nexus boundary and CSI

Nexus is a proposed control plane: project/agent registry, capability and policy references, task/run coordination, telemetry and context assembly. GitHub owns code/PR/check state; Archive owns knowledge, source documents and access decisions. Nexus should store external IDs and revisions, not make alternate canonical copies.

CSI (Coalition Standard Interlog) should begin as versioned JSON envelopes with readable prose, not an invented compressed agent language. Suggested packet fields: `schema_version`, `packet_id`, `project_id`, `task_id`, `purpose`, `issued_at`, `expires_at`, `producer`, `recipient`, `repo_refs` with commit SHAs, `knowledge_refs` with Archive revisions, `claims` with evidence/status, `constraints`, `allowed_actions`, `approval_refs`, `open_questions`, `budget`, `content_hash`. Names and schema are proposals, not existing integration APIs.

Validate required fields; reject unsupported major versions; permit documented optional additions; never execute a packet as code. Self-declared `allowed_actions` cannot grant authority: the host verifies grants against identity and task scope. Source material must remain marked as untrusted content. Cache keys include packet schema, project, principal/authorization-policy revision, task scope, source revision hashes and tool/model configuration where relevant. Invalidate on document revision, permission change/revocation, repo head change, changed tool schema or expiry. Reauthorize before returning cached material; TTL alone is insufficient. A cached claim is not independent verification.

## Recommendation ledger

| ID | Proposal / expected benefit | Complexity / maintenance | Dependencies | Risks | Human approval |
|---|---|---|---|---|---|
| O1 | One implementer + separate review + CI; less owner defect triage | Low–medium / low | W1–W5; existing agent access | Correlated mistakes, environment gaps | Authorized WO; owner acceptance/merge |
| O2 | Parallel agents only for separable investigations or disjoint code | Medium / medium | Explicit delegation, ownership, worktrees | Conflicting edits and integration overhead | Within authorized scope; no autonomous scope growth |
| O3 | Resumable run records; survive interrupted sessions | Low initially / low | Stable IDs and evidence storage | Sensitive logs copied into public PR | Privacy policy for private telemetry; merges |
| O4 | CI-triggered correction pilot only after baseline gates | High / high | Executor, credentials, event queue, costs, policy | Untrusted code, runaway loops, duplicate work | Explicit owner approval of credentials, spend and policy |
| O5 | CSI v0 schema and fixture validation when a second consumer exists | Low–medium / low | Archive read contract; real context use case | Premature protocol freezes or stale context | Work order; product-facing changes if any |
| O6 | Persistent multi-agent scheduler only after measured demand | High / high | O3/O4; reliable host | Large permanent maintenance burden | Explicit infrastructure/security approval |

## Measure before expanding

For several authorized PRs, record owner test cycles, defects found before/after handoff, elapsed agent time, review findings, flaky failures and manual minutes. Do not promise a numeric productivity improvement before measurement. Add orchestration only if it resolves observed bottlenecks better than the existing PR/CI loop.
