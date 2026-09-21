# GSI Working Instructions

## Project identity

GSI means Genome Stability Inducers.

It is a personal, generated music archive: part review collection, part memory system, part visual listening environment. It is not currently intended to be a generic public review platform.

Preserve its personal language and unusual section names. Do not normalize it into a generic music website without explicit approval.

## Working method

- Inspect the current implementation before proposing changes.
- Explain proposed changes before editing.
- Wait for explicit approval before substantial UI, architecture, or data-model changes.
- Prefer small, named patches over broad rewrites.
- Do not replace whole files merely to make a small adjustment.
- State which files and functions will change.
- Explain unfamiliar Python, HTML, CSS, and JavaScript notation.
- Preserve the user's original capitalization and wording.
- Never silently change album-title casing.
- Avoid adding UI elements merely because they are conventional.

## Source-of-truth rules

- `entries/*.md` contains irreplaceable user writing.
- Never overwrite or remove review prose.
- Existing entry metadata may be synchronized, but review sections must be preserved.
- `site/` is generated output.
- Do not manually implement lasting features only inside generated HTML.
- Edit source logic, templates, configuration, or assets instead.

## Validation

After Python changes, run:

    python -m py_compile build.py

After config changes, run:

    python -m json.tool config.json

After relevant changes, run:

    python build.py

Report all warnings and errors. Do not claim success merely because Python compiled; inspect generated HTML/CSS/JavaScript when those layers changed.

## Current architectural policy

Do not modularize the entire project before GSI 1.0 without explicit approval.

The likely post-1.0 refactor will:

1. Extract CSS from Python.
2. Extract JavaScript from Python.
3. Introduce HTML templates, probably Jinja.
4. Add validation and tests.
5. Split Python into modules only where useful.

## UI principles

- Homepage: archive wall / signal room / distorted music-selection environment.
- Entry pages: intimate album shrine / listening room.
- Filter controls should clearly look interactive.
- Album metadata should not look like buttons.
- Streaming links should look like outbound links, not toggles.
- Mobile behavior must not rely solely on hover.
- Album accents should remain controllable through manual overrides.
- Do not lock the project into a single genre or make it resemble a Metric fan page.

## Current priority

First audit the repository and reconcile it with `PROJECT_STATE.md`.

Do not immediately refactor or redesign.
