# Archive v0 TODO

## Context View

- Add a **Continuous Reading** toggle that hides repeated chunk cards and
  metadata, joins one semantic unit into a readable flow, and retains subtle
  page/chunk anchors for navigation.

## Document Recovery

- Validate figure extraction across varied diagrams, photographs, charts, and
  multi-panel captions before running a whole-document figure scan.
- Improve geometric reconstruction of stacked fractions and other display
  mathematics whose glyph order remains ambiguous in plain text.
- Capture and repair the odd table representations around Machinery's Handbook
  PDF pages 262–263 as focused regression samples.

## UI and Source Navigation

- Continue the UI-polish pass with progressive disclosure: keep content and
  primary actions prominent, and place technical metadata in expandable details.
- Add safe folder/category creation and note-moving tools to Notes Curator so
  users can organize notes without entering arbitrary filesystem paths.
- Add hierarchy-based breadcrumbs across document views now that front matter
  and table-of-contents entries are grouped for navigation.
- Add a theme customizer after the shared color variables and component styles
  have stabilized.
- Render extracted table-of-contents items as clickable links to the matching
  section start. Resolve targets from hierarchy and printed-page metadata, with
  a plain-text fallback when no trustworthy structural destination exists.
- Specify and prototype the interactive **blorb tree**: a document-organization
  view whose child branch blorbs expand from a parent on hover or focus. Start
  after the hierarchy cleanup and initial UI pass, but before treating the UI
  architecture as final.
