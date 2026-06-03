# Project Name + Tag Auto-generation — EARS Specifications

## Unit 1: Name field

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL render a required "Name" text input above the Tag field in the New Project modal. |
| R-1.2 | WHEN the Name field is empty, THE SYSTEM SHALL disable the "Create project" button. |
| R-1.3 | WHEN the form is reset or closed, THE SYSTEM SHALL clear the Name field. |

## Unit 2: Auto-derivation of Tag from Name

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the user types in the Name field AND the Tag has not been manually edited, THE SYSTEM SHALL update the Tag field to `toTag(name)` where `toTag` = trim → uppercase → replace non-alphanumeric runs with `-` → strip leading/trailing dashes. |
| R-2.2 | WHEN the derived Tag is an empty string (e.g. name is only symbols), THE SYSTEM SHALL leave the Tag field empty rather than setting an invalid value. |
| R-2.3 | WHILE the Tag has not been manually edited, THE SYSTEM SHALL keep the Tag in sync with every keystroke in the Name field. |

## Unit 3: Manual Tag override

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the user types directly in the Tag field, THE SYSTEM SHALL mark the Tag as manually edited and stop auto-syncing from the Name field. |
| R-3.2 | WHEN the form is reset, THE SYSTEM SHALL clear the manually-edited flag so auto-sync resumes on next open. |
| R-3.3 | THE SYSTEM SHALL still validate the manually-entered Tag against `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` before submission. |

## Unit 4: API & markdown rendering

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the form is submitted, THE SYSTEM SHALL include `name` (the raw Name field value, trimmed) in the `NewProjectRequest` payload alongside `tag`. |
| R-4.2 | IF `name` is empty after trim, THE SYSTEM SHALL prevent submission and show "Project name is required." |
| R-4.3 | WHEN the backend scaffolds the project markdown page, THE SYSTEM SHALL render the H1 heading as `# {name}` using the submitted name value. |
| R-4.4 | IF `name` is absent or empty in the backend call (e.g. CLI, legacy callers), THE SYSTEM SHALL fall back to `# {tag}` for the H1 heading. |
| R-4.5 | THE SYSTEM SHALL NOT store `name` in the YAML frontmatter of the project page. |
