# Archive engineering instructions

- Preserve original sources, authored content, stable identifiers and unknown metadata.
- Read the work order and current README before changing code. Stay within its allowed files and behavior.
- Run the README's pinned Python 3.12 verification recipe. Never test against live notes or personal PDFs. The verification wrapper copies tracked source into a disposable directory.
- Record base/candidate SHA, exact commands, counts, skips, failures and environmental limits. Collection or YAML inspection is not passing execution.
- Use at most three corrective iterations and two separate review rounds, with a 90-minute default active budget. Stop on external blockers or scope expansion with a checkpoint.
- Separate review must be performed by another agent/person. Label self-review honestly.
- Use a branch and consolidated draft PR with evidence, limitations, acceptance and rollback. Never merge automatically.
- Workflow standard: PR #44, docs/wo-001/ENGINEERING_WORKFLOW.md (until available on main).
