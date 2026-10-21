# Progress Tracker

Update this file after every meaningful implementation change: check
off the unit you just finished, move it from "Next Up" to
"Completed", update "Current Phase"/"Current Goal", and add a
Session Note. Each unit below is meant to be implemented in its own
session/prompt — never implement more than one unit at a time unless
explicitly told to.

## Current Phase

- Phase 6 — Gemini Integration & AI Field Generation

## Current Goal

- Unit 6.1 — Gemini API client wrapper.

## Completed

- Unit 0.1 — scaffold the new apps.
- Unit 0.2 — wire URLs and dashboard.
- Unit 1.1 — Project model & CRUD.
- Unit 1.2 — Settings model & page.
- Unit 2.1 — Contact model & CSV import.
- Unit 2.2 — Contacts list/table view.
- Unit 2.3 — CSV re-upload merge logic.
- Unit 3.1 — SequenceStep model & CRUD.
- Unit 4.1 — Template model & CRUD.
- Unit 4.2 — Placeholder classification utility.
- Unit 4.3 — Drag-and-drop rich-text template editor.
- Unit 5.1 — AIPromptConfig model & AI configure view.
- Unit 5.2 — Manual input detection & auto-formatting.

## In Progress

- None yet.

## Next Up

- Unit 6.1 (see Phase & Unit Roadmap below)

## Open Questions

- None. All product and technical decisions for this build are final
  and recorded in project-overview.md, architecture.md, and the
  Architecture Decisions section below. Do not re-ask the user about
  anything covered there — follow what's written.

## Architecture Decisions

- **Base**: start from `andyjud/django-starter` as-is (CustomUser
  auth, `_core`/`a_home`/`a_users`), then add new apps —
  `a_projects`, `a_sequences`, `a_contacts`, `a_generation` —
  following the starter's `a_`-prefixed app-naming convention.
- **Single user**: no teams/multi-tenancy; auth exists only because
  the starter ships it. No per-user data isolation features beyond
  `request.user` ownership checks.
- **Contact storage**: each `Contact` stores its full CSV row as a
  single JSON field (`data`) rather than a dynamic per-column table,
  so projects can have arbitrary/different CSV columns without
  schema changes.
- **CSV re-upload**: merge-only. Match existing contacts by the
  project's `key_column`; insert unmatched rows; never update or
  delete existing contacts on re-upload.
- **Key column**: chosen by the user at first CSV upload (suggested
  default `email` for Email projects, `linkedin` for DM projects);
  fixed afterward.
- **Condition operators**: `equals`, `not_equals`, `contains`,
  `is_empty`, `is_not_empty`, `greater_than`, `less_than`. Multiple
  conditions on one template are always ANDed.
- **Template resolution**: explicit top-to-bottom priority order;
  first full match wins; exactly one condition-less default template
  per sequence step acts as the fallback.
- **Placeholder classification**: a `{{token}}` found in a
  Subject/Body is CSV-sourced if it case-insensitively matches a
  project CSV column; otherwise it's AI-sourced.
- **AI prompt scope**: one `AIPromptConfig` per template. One prompt
  → one Gemini call → one or more named tagged outputs, each mapped
  to one AI-sourced placeholder in that template's Subject/Body.
- **AI prompt inputs**: a `{{token}}` inside the prompt text that
  matches a CSV column is auto-filled from the contact's row; any
  other `{{token}}` in the prompt is a **manual input**, filled via a
  one-off text box shown right before generation and never persisted
  anywhere.
- **Auto-formatting**: the app always appends its own formatting
  instructions to the user's prompt text before sending it to Gemini,
  telling it to wrap each expected output value in an XML-style tag
  named after that placeholder — the user never hand-writes this
  part.
- **Two-step generation**: "Generate AI Fields" (calls Gemini, saves
  `GeneratedAIField` rows) and "Generate Email/DM" (pure
  substitution from CSV + saved AI fields, no Gemini call) are always
  separate, manual, per-contact, per-step actions.
- **Overwrite, no versioning**: every regeneration (AI fields or
  final message) overwrites the previous saved value for that exact
  (contact, step, placeholder/message). No history is kept anywhere.
- **Due dates**: non-strict. Each `SequenceStep` has a
  `default_due_offset_days`; after a message is generated for step
  N, the contact's `next_due_date` is auto-set to
  `generated_at + step (N+1).default_due_offset_days` and
  `current_step` auto-advances — but both fields remain freely,
  manually editable at any time with no validation blocking a
  change.
- **Error isolation**: a Gemini failure (bad key / rate limit /
  quota) is caught per contact/row, stored, and shown inline with a
  retry action; it never blocks or fails other rows in the same
  batch.
- **Editor**: the drag-and-drop template editor is a `contentEditable`
  field with small vanilla-JS drag/drop handlers (CSV column chips →
  insert `{{Column}}` at cursor). This is the one deliberate
  exception to "frontend must use htmx" — htmx cannot do client-side
  cursor-position text insertion, and this interaction needs no
  server round-trip.
- **Settings/API key**: stored as a plain text field on a single-row
  `Settings` model — no encryption, no key rotation UI, no per-user
  key (single-user app).

## Phase & Unit Roadmap

Work through phases in order. Within a phase, units are numbered and
should also be done in order unless a unit says otherwise. Each unit
is sized to be implemented in one focused session/prompt.

### Phase 0 — Base Setup

- [x] **0.1** Set `PROJECT_TITLE` in
      `_core/settings.py`, run migrations, confirm signup/login/
      email-confirmation works unmodified. Create four new empty
      Django apps: `a_projects`, `a_sequences`, `a_contacts`,
      `a_generation`, registered in `INSTALLED_APPS`.
- [x] **0.2** Wire the new apps' `urls.py` into the root URLConf.
      Build a minimal authenticated dashboard template (extends the
      starter's base template/nav) that will later list projects;
      make it the post-login redirect target.

### Phase 1 — Projects & Settings

- [x] **1.1** `Project` model (`name`, `type` = `email`|`linkedin_dm`,
      `key_column` nullable, `csv_columns` JSON list, `created_at`,
      owner FK to the user). Views: create, list, delete (with
      confirmation). All scoped to `request.user`.
- [x] **1.2** Single-row `Settings` model (`gemini_api_key`). Settings
      page (GET shows current key masked/plain as you prefer, POST
      updates it). Helper function elsewhere in the codebase to fetch
      the current key.

### Phase 2 — CSV Import & Contacts

- [x] **2.1** `Contact` model (`project` FK, `data` JSON field,
      `current_step` integer/FK placeholder, `next_due_date` nullable
      date). CSV upload form: file input + a key-column dropdown
      populated from the parsed CSV header row (pre-selected to
      `email`/`linkedin` based on project type if present). On
      submit: store `csv_columns` on the `Project`, set
      `key_column`, and create one `Contact` per row.
- [x] **2.2** Contacts list/table view for a project: columns are
      built dynamically from `project.csv_columns`, plus
      current-step and due-date columns.
- [x] **2.3** Re-upload flow: same upload form, but this time match
      incoming rows against existing contacts by `key_column` value
      (case-insensitive, trimmed); only insert rows with no match;
      leave every existing `Contact` row untouched. Show a summary
      after upload (e.g. "12 new contacts added, 8 already existed").

### Phase 3 — Sequence Steps

- [x] **3.1** `SequenceStep` model (`project` FK, `name`, `order`,
      `default_due_offset_days`). CRUD UI: set the initial number of
      steps when first configuring a project's sequence; add/remove/
      reorder steps later; edit each step's name and due-day offset.

### Phase 4 — Templates & Conditions

- [x] **4.1** `Template` model (`sequence_step` FK, `order`,
      `subject` nullable — used only when `project.type == email`,
      `body` text). `TemplateCondition` model (`template` FK,
      `column_name`, `operator`, `value`). CRUD UI per sequence step:
      one always-present default template (no conditions, not
      deletable), plus add/remove/reorder condition templates, each
      with its own list of ANDed conditions (column dropdown from
      `project.csv_columns`, operator dropdown, value input — value
      input hidden for `is_empty`/`is_not_empty`).
- [x] **4.2** Shared placeholder-parsing utility function (extracts
      `{{...}}` tokens from any text, trims/normalizes them) used
      here to classify each template's placeholders as CSV-sourced
      vs. AI-sourced; show this classification under the Subject/
      Body fields in the template edit UI (e.g. "CSV: Name, Sponsor
      · AI: specifics_about_recent_video").
- [x] **4.3** Drag-and-drop rich-text template editor: replace the
      plain Subject/Body inputs with `contentEditable` fields; render
      the project's CSV columns as draggable chips beside the editor;
      dropping a chip inserts `{{Column Name}}` as text at the drop/
      cursor position via vanilla JS. Submits as plain text alongside
      the rest of the template form (still a normal htmx/Django form
      post — only the insertion interaction is client-side JS).

### Phase 5 — AI Prompt Configuration

- [x] **5.1** `AIPromptConfig` model (`template` OneToOne,
      `prompt_text`). "Configure AI" view per template: only shown/
      relevant when the template has at least one AI-sourced
      placeholder (per 4.2's classification); lists those expected
      output placeholder names and provides the `prompt_text` field.
- [x] **5.2** Apply the placeholder utility to `prompt_text` itself to
      detect manual-input tokens (any `{{token}}` in the prompt that
      isn't a CSV column); store/display that list for later use by
      Phase 6's generation form. Implement the auto-appended
      formatting instruction: before sending to Gemini, the stored
      `prompt_text` (after substitution) is concatenated with a
      generated instruction block listing every expected output tag
      name and requiring the response to wrap each value in that
      exact tag, nothing else.

### Phase 6 — Gemini Integration & AI Field Generation

- [ ] **6.1** Gemini API client wrapper: server-side POST to the
      Gemini free-tier endpoint using the key from `Settings`;
      normalize failure modes (missing/invalid key, rate limit,
      quota exceeded, generic error) into a single error type/message
      the UI can display.
- [ ] **6.2** `GeneratedAIField` model (`contact` FK, `template` FK,
      `placeholder_name`, `value`, `status` = success|error,
      `error_message`, `generated_at`). "Generate AI Fields" view for
      one contact + sequence step: resolve the matching template
      (reuse 7.1's resolver once it exists, or build the resolver
      here and reuse it in Phase 7 — see note on ordering below),
      render a text box for each manual-input field detected in 5.2,
      on submit substitute CSV + manual values into the prompt, call
      the Gemini wrapper, parse the tagged response into one
      `GeneratedAIField` row per expected placeholder (overwriting
      any existing row for that contact/template/placeholder), and
      show per-field success/error inline with a retry action on
      failure.
      > Note: if it's cleaner to build the template-resolution
      > function once and share it between this unit and 7.1, build
      > it here first and import it in Phase 7 rather than
      > duplicating it.

### Phase 7 — Email/DM Generation & Review

- [ ] **7.1** Template-resolution function: given a contact and a
      sequence step, evaluate that step's condition templates in
      order and return the first full match, or the default template
      if none match. (Skip if already built in 6.2 — just confirm it
      is shared, not duplicated.)
- [ ] **7.2** `GeneratedMessage` model (`contact` FK, `sequence_step`
      FK, `template_used` FK, `subject` nullable, `body`,
      `generated_at`). "Generate Email/DM" view: resolve the
      template, substitute CSV placeholders directly and AI
      placeholders from the latest matching `GeneratedAIField` rows;
      if any AI-sourced placeholder has no saved value, fail with a
      message naming the missing placeholder(s) and pointing the
      user at "Generate AI Fields"; otherwise save/overwrite the
      `GeneratedMessage`, and auto-update the contact's
      `current_step`/`next_due_date` per the due-date decision above.
- [ ] **7.3** Results/review view: per project, a table of every
      contact × sequence step; each cell shows generation status
      (not generated / generated) with an Open action that shows
      Subject (Email projects only) and Body with one-click copy.
      Also surface, per contact: current step (dropdown, manually
      overridable) and due date (date input, manually overridable),
      independent of the generation actions.

### Phase 8 — Deletion & Cleanup

- [ ] **8.1** Project delete flow: confirmation step, then cascade
      delete (rely on Django FK `on_delete=CASCADE` through the
      whole chain — sequence steps, templates, conditions, AI prompt
      configs, contacts, generated AI fields, generated messages).
      Manually verify after deletion that no related rows remain in
      any table.

### Phase 9 — Polish

- [ ] **9.1** Pass over every view built in Phases 1–8: add empty
      states (no projects yet, no contacts yet, no templates yet),
      loading states for Gemini calls, and consistent error
      rendering. Do a final manual walkthrough against every item in
      project-overview.md's "Success Criteria" section and fix
      anything that doesn't hold.

## Session Notes

- Before starting any unit, read `project-overview.md` and
  `architecture.md` in full — they contain the finalized product and
  technical decisions and should not be re-derived or re-questioned.
- Implement exactly one unit per session unless told otherwise.
- At the end of a session, update this file: check off the unit,
  move it into "Completed", update "Current Phase"/"Current Goal"/
  "Next Up", and add a one- or two-line note here about what was
  built and anything the next session needs to know (e.g. "7.1's
  resolver function lives in `a_generation/resolution.py`, imported
  by both 6.2 and 7.2").

- **Unit 0.1 completed**: Set `PROJECT_TITLE` to "Email Marketing App" in `_core/settings.py`, ran migrations successfully, confirmed starter's signup/login/email-confirmation flow works (server starts cleanly, allauth URLs included). Created four empty Django apps (`a_projects`, `a_sequences`, `a_contacts`, `a_generation`) with default scaffolding and registered all four in `INSTALLED_APPS`.

- **Unit 0.2 completed**: Created `urls.py` for all four new apps (`a_projects`, `a_sequences`, `a_contacts`, `a_generation`) and wired them into the root URLConf under `/projects/`, `/sequences/`, `/contacts/`, `/generation/`. Added `a_home/urls.py` with a `dashboard_view` protected by `@login_required`, created `a_home/templates/a_home/dashboard.html` extending `layouts/page.html` with a "Projects" heading. Updated `LOGIN_REDIRECT_URL` in settings to `'a_home:dashboard'`. Server starts cleanly.

- **Unit 1.1 completed**: Created `Project` model in `a_projects/models.py` with fields: `name`, `type` (choices: email/linkedin_dm), `key_column` (nullable), `csv_columns` (JSON list), `created_at`, and `owner` FK to user. Built create/list/delete views using class-based views (ProjectListView, ProjectCreateView, ProjectDeleteView) with htmx partials for create form and delete confirmation. All views scoped to `request.user`. Created templates: list view with project cards showing type badge, name, creation date, and actions; htmx partials for create form, project row, and delete modal. Wired URLs in `a_projects/urls.py` and updated dashboard to show project list with htmx-powered create/delete. Migrations applied successfully, server runs cleanly.

- **Unit 1.2 completed**: Added `Settings` model in `a_projects/models.py` with single-row enforcement (pk=1) and `gemini_api_key` TextField. Created `settings_view` in `a_projects/views.py` (GET shows current key, POST updates it, creates row on first access via `Settings.get_settings()`). Added `a_projects/settings_utils.py` with `get_gemini_api_key()` helper for other apps to import. Created `a_projects/templates/a_projects/settings.html` with password input for API key, link to Google AI Studio, and status indicator. Added URL `/projects/settings/` in `a_projects/urls.py`. Added "App Settings" link to user dropdown in `templates/includes/header.html`. Migration applied, server runs cleanly.

- **Unit 2.3 completed**: Updated `csv_upload_view` in `a_contacts/views.py` to implement merge-on-re-upload logic. When a project already has a `key_column` set, re-upload compares incoming rows' key values (case-insensitive, trimmed) against existing contacts' key values. Matching rows are skipped (existing contacts never updated/deleted); only new rows are inserted. Header lists are merged (union, preserving original order then appending new columns) and `project.csv_columns` is updated. Summary message shows counts: "X new contacts added, Y already existed and were left unchanged." Key column dropdown is disabled on re-upload with fixed value shown. Updated upload template and partial to reflect re-upload state. Server runs cleanly.

- **Unit 3.1 completed**: Created `SequenceStep` model in `a_sequences/models.py` with `project` FK, `name`, `order`, `default_due_offset_days` (default 2). Built `sequence_configure_view` in `a_sequences/views.py` with full CRUD: initial step creation via number input, add/remove steps, inline editing of name and due offset, drag-and-drop reordering (vanilla JS), and delete with confirmation. Added URL `/sequences/project/<pk>/configure/` in `a_sequences/urls.py`. Created templates: main configure page with step list, partial for step rows with drag handles. Linked from project detail view via "Configure Sequence" button. Migration applied, server runs cleanly.

- **Unit 4.1 completed**: Created `Template` model (`sequence_step` FK, `order`, `subject` nullable for email, `body`) and `TemplateCondition` model (`template` FK, `column_name`, `operator` with 7 choices, `value` blank for is_empty/is_not_empty). Built `template_configure_view` with full CRUD: default template (order=0, no conditions) auto-created per step and protected from deletion; add/remove/reorder condition templates via htmx; inline editing of subject/body; drag-and-drop reorder of condition templates; dynamic add/remove of conditions per template with column dropdown from `project.csv_columns`, operator dropdown, value input hidden for is_empty/is_not_empty. Added URL `/sequences/project/<pk>/step/<step_pk>/templates/`. Templates use plain textareas (rich editor in Unit 4.3). Migration applied, server runs cleanly.

- **Unit 4.2 completed**: Created `a_sequences/placeholders.py` with `extract_placeholders()` (extracts `{{...}}` tokens, trims, deduplicates preserving order), `classify_placeholders()` (CSV-sourced vs AI-sourced via case-insensitive match against `project.csv_columns`), and `get_placeholder_classification()` convenience function. Updated `template_configure_view` to compute classification for each template's subject+body and attached as `template.placeholder_classification`. Updated `template_list.html` partial to display classification badges under Body field: green "CSV: ..." for matched columns, purple "AI: ..." for unmatched. Invariant 3 satisfied: placeholders matching CSV columns (case-insensitive, trimmed) are CSV-sourced; others are AI-sourced.

- **Unit 4.3 completed**: Replaced plain `<textarea>` inputs with `contentEditable` `<div>` fields in `a_sequences/partials/template_list.html` (subject for email projects, body for all). Added CSV column chips as draggable elements in `placeholder-chips` container. Created `static/js/template-editor.js` (vanilla JS, no framework/build step) handling: `dragstart` on chips, `dragover`/`drop` on contentEditable fields to insert `{{Column Name}}` at cursor position via `Range`/`Selection` API, and `input` event to sync content to hidden form fields (`template_<pk>_subject`, `template_<pk>_body`). Form submission serializes contentEditable text into same backend fields; Unit 4.2 classification continues to work on submitted text. Subject field omitted for `linkedin_dm` projects. Only the insertion interaction uses vanilla JS — rest of UI remains htmx/Django.

- **Unit 5.1 completed**: Created `AIPromptConfig` model in `a_sequences/models.py` with `template` OneToOneField and `prompt_text` TextField. Added `get_expected_output_placeholders()` method to derive AI-sourced placeholders live from template's subject/body using the shared placeholder utility. Built `ai_prompt_configure_view` in `a_sequences/views.py` that: checks for AI-sourced placeholders (redirects with message if none), displays expected output placeholder names as badges, provides prompt_text textarea with guidance on CSV column and manual input syntax, saves prompt on POST. Added URL `/sequences/project/<pk>/step/<step_pk>/template/<template_pk>/ai/` in `a_sequences/urls.py`. Created `a_sequences/templates/a_sequences/ai_prompt_configure.html` with expected outputs display and prompt textarea. Added "Configure AI" link in `template_list.html` partial shown only when template has AI-sourced placeholders. Migration applied, server runs cleanly.

- **Unit 5.2 completed**: Added `get_prompt_manual_inputs()` to `a_sequences/placeholders.py` to detect manual-input tokens in prompt text (tokens not matching CSV columns). Created `a_sequences/ai_formatting.py` with `build_gemini_prompt()` that appends auto-generated formatting instructions requiring XML-style tagged output for each expected placeholder. Updated `ai_prompt_configure_view` to display manual inputs as amber badges under "Detected Manual Input Fields" section. Updated `ai_prompt_configure.html` to show manual inputs. Tested both functions: manual input detection correctly identifies non-CSV tokens, and formatting function wraps outputs in `<placeholder>[value]</placeholder>` tags.
