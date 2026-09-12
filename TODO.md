# Archive v0 TODO

## Context View

- Add a **Continuous Reading** toggle that hides repeated chunk cards and
  metadata, joins one semantic unit into a readable flow, and retains subtle
  page/chunk anchors for navigation.
- Fix table and figure previews in the scrolling structure/chunk list. Use
  artifact-aware summaries or thumbnails instead of clipped or misleading
  flattened content.

## Document Recovery

- Validate figure extraction across varied diagrams, photographs, charts, and
  multi-panel captions before running a whole-document figure scan.
- Improve geometric reconstruction of stacked fractions and other display
  mathematics whose glyph order remains ambiguous in plain text.

## UI and Source Navigation

- Run a focused UI-polish pass once the current handbook hierarchy and artifact
  recovery are stable enough to design against. Review information density,
  chunk-list scanning, controls, navigation, and small-screen behavior while
  preserving the current intuitive workflow.
- Render extracted table-of-contents items as clickable links to the matching
  section start. Resolve targets from hierarchy and printed-page metadata, with
  a plain-text fallback when no trustworthy structural destination exists.
- Specify and prototype the interactive **blorb tree**: a document-organization
  view whose child branch blorbs expand from a parent on hover or focus. Start
  after the hierarchy cleanup and initial UI pass, but before treating the UI
  architecture as final.
