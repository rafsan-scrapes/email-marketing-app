# Email Marketing App

## Overview

A local-only, single-user Django web application for running manual,
template-based cold outreach campaigns over email or LinkedIn DM. The
user creates a project per campaign, uploads a CSV of contacts,
defines a multi-step message sequence with conditional template
variants, and generates each message on demand (optionally using
Google Gemini to fill placeholders that can't come from the CSV). The
user copies the generated subject/body themselves and sends it
manually outside the app — the app never sends anything on its own.
AI is a light touch on top of this: the core job of the app is
producing copy-pasteable, bulk-ready email/DM text from a CSV.

## Goals

1. Let one person run multiple outreach campaigns (email or LinkedIn
   DM), each with its own CSV-sourced contact list and multi-step
   sequence of templates.
2. Support conditional template selection per sequence step so the
   right message variant is chosen automatically based on CSV data.
3. Let AI (Gemini) fill template placeholders that cannot be sourced
   from the CSV, driven by a per-template configurable prompt (with
   an optional per-contact override — see "Contact Dashboard & Bulk
   Generation" below), with no code changes required to add a new
   AI-backed campaign.
4. Keep every generated email/DM retrievable and copyable until the
   user explicitly deletes the project.
5. Let the user work through many contacts at once from a single
   dashboard — setting optional per-contact AI prompts, and
   triggering AI-field generation and message generation in bulk —
   rather than one contact at a time.

## Core User Flow

1. Sign up / log in (email + password, single local user).
2. Settings → enter Gemini API key.
3. Create Project → enter name, choose type: **Email** or
   **LinkedIn DM**.
4. Upload CSV → choose the key column (suggested default: `email`
   for Email projects, `linkedin` for DM projects, but any column
   can be chosen) → contacts are imported.
5. Configure Sequence Steps → set how many steps the campaign has
   (editable later), name each step, set a default due-day offset
   per step.
6. Configure Templates per Step → write the default template
   (Subject + Body for Email, Body only for DM) using `{{Column}}`
   placeholders, dragged in from the CSV column list or typed
   directly; add any number of condition-override templates.
7. Configure AI (optional, per template) → for any template whose
   placeholders don't match a CSV column, write a default prompt
   that outputs those placeholder values inside named tags; the
   prompt itself may reference CSV columns and/or one-off
   manual-input fields.
8. Work the Contact Dashboard, per project:
   a. Optionally click **Set Prompt** on any contact (for the
      currently-selected sequence step) to give that specific
      contact its own custom AI prompt, replacing the template's
      default prompt just for them. Leave it unset to use the
      template default.
   b. Select contacts (individually or in bulk) and click **Send
      Prompt** to run AI-field generation for the selected step —
      using each contact's own prompt override where set, the
      template default otherwise. A failed Gemini call for one
      contact never blocks the rest.
   c. Whenever ready, select contacts and click **Generate Email/DM**
      to substitute CSV values and any saved AI field values into
      the matching template and save the result. If a template
      needs an AI-sourced placeholder that hasn't been generated
      yet for a contact, that contact's generation fails with a
      clear message pointing back to Send Prompt — other selected
      contacts are unaffected.
9. Review & Copy → from the dashboard, **Open** any contact to see
   their generated messages across every sequence step together, and
   copy the Subject and/or Body of any of them.
10. Track → see each contact's current step and due date; manually
    advance the step or change the due date at any time — nothing
    about due dates is enforced or automated beyond suggesting the
    next date.
11. Delete Project → removes the project and everything that
    belongs to it (sequence, templates, contacts, prompts, generated
    messages).

## Features

### Authentication

- Email + password signup/login, using django-starter's existing
  `a_users` CustomUser app (including its email-confirmation flow).
- Built for a single local user; no team or multi-tenant concept.

### Projects

- Create, list, and delete projects.
- Each project has a fixed type — **Email** or **LinkedIn DM** — set
  at creation. The type determines whether templates have a Subject
  field (Email) or Body only (DM).

### Contacts (CSV)

- Upload a CSV per project.
- The user selects the **key column** on first upload (the column
  whose value uniquely identifies a contact — typically `email` for
  Email projects or `linkedin` for DM projects, but any header can
  be chosen). The key column is fixed once set.
- Re-uploading a CSV **merges** by key column: any row whose key
  value already exists is left completely untouched; only rows with
  a new, unmatched key value are inserted. Existing contacts are
  never updated or removed by a re-upload.
- A contacts table shows every CSV column plus the contact's current
  step and due date.

### Sequences

- The user sets the number of sequence steps when creating the
  sequence (editable afterward — steps can be added, removed, and
  reordered).
- Each step has a name, an order, and a **default due-day offset**
  (days after the previous step's generation) used to pre-fill the
  next due date. This is a suggestion only — never enforced.

### Templates & Conditions

- Each sequence step has **exactly one default (condition-less)
  template**, which acts as the fallback, plus any number of
  condition-override templates.
- Condition-override templates are evaluated **top to bottom in an
  explicit priority order**; the **first template whose conditions
  all match wins**. If none match, the default template is used.
- A single template's conditions are always **ANDed** together (all
  must be true for that template to match). Supported operators:
  `equals`, `not equals`, `contains`, `is empty`, `is not empty`,
  `greater than`, `less than`.
- Templates use `{{Placeholder}}` syntax. A placeholder that matches
  a CSV column (case-insensitive, trimmed) is substituted directly
  from that contact's row. A placeholder that matches no CSV column
  is **AI-sourced**.
- Subject/Body are edited in a rich-text, drag-and-drop editor: the
  project's CSV columns are shown as draggable chips that insert
  `{{Column Name}}` at the cursor when dropped.
- Templates are **universal** — the same template content is shared
  by every contact that resolves to it. Personalization beyond the
  CSV happens through AI prompts (template-level default, or the
  optional per-contact override below), not by editing the template
  itself per contact.

### AI-Generated Placeholders

- AI generation is configured **per template** by default: one
  prompt can produce one or more named output values in a single
  Gemini call.
- The prompt text may reference `{{CSV Column}}` placeholders
  (auto-filled from the contact's row) and `{{manual_field}}`
  placeholders — any token in the prompt that isn't a CSV column is
  treated as a **manual input**, filled via a one-off text box shown
  right before generation and never saved anywhere.
- The app automatically appends formatting instructions to every
  prompt telling Gemini to wrap each expected output value in a tag
  matching that placeholder's name (e.g. `<specifics_about_video>
  ...</specifics_about_video>`), so the response can always be
  parsed automatically — the user never has to hand-write the
  formatting instructions themselves. This formatting block is
  always derived from the resolved template's expected output
  placeholders, regardless of whether the default template prompt
  or a contact-level override prompt (below) supplies the base text.
- **Generate AI Fields** (surfaced from the dashboard as **Send
  Prompt** — see below) is a separate, manual action that must be
  run (when needed) *before* **Generate Email/DM**. The two are
  never combined into one click.
- The Gemini API key lives on the Settings page (Gemini free tier:
  https://aistudio.google.com/app/api-keys).
- A failed Gemini call (bad key, rate limit, quota) shows a clear
  inline error on that specific contact/row only, with a retry
  action; it never blocks or fails generation for any other contact
  — including when triggered in bulk from the dashboard.

### Contact Dashboard & Bulk Generation

- Each project has a dashboard: one row per contact, with a single
  **step selector** above the table (applies to the whole table, not
  per-row) that determines which sequence step the row statuses and
  the two bulk action buttons below operate on.
- Columns per row: the project's key-column value; **Set Prompt** —
  opens an editor for that contact's optional, custom AI prompt for
  the selected step; an AI-fields status indicator with a link to
  see the generated values/placeholders (on the existing Generate AI
  Fields page — raw values are not shown inline in the dashboard
  table); a message-generation status indicator; and an **Open**
  action.
- **Per-contact prompt override**: optional and set per
  (contact, step) — not shared across steps, and not required. When
  set, it **fully replaces** the template's default AI prompt for
  that contact's generation at that step; when left blank, the
  template's default prompt is used exactly as it is without this
  feature. The prompt's own job is unchanged from the template-level
  version: its Gemini output still fills the template's AI-sourced
  placeholder(s) for that contact.
- **If no prompt is available** (no override, and the template's
  default prompt can't produce the needed values) for a template
  that needs AI-sourced placeholders, those placeholders are simply
  left ungenerated. Attempting **Generate Email/DM** for that
  contact then fails with a clear error naming the missing
  placeholder(s) and telling the user to run Send Prompt first —
  exactly as it already does today for the single-contact flow.
- **Bulk selection**: rows are checkbox-selectable (individually or
  all at once). Two buttons sit above the table:
  - **Send Prompt** — runs AI-field generation for every selected
    contact at the selected step (each contact's own prompt override
    if set, otherwise the template default). Each contact's prompt
    text is unique to them; the template and its expected output
    placeholders stay the same across all of them.
  - **Generate Email/DM** — runs message generation for every
    selected contact at the selected step, once the user is ready
    (not necessarily right after Send Prompt).
  - Both bulk actions isolate failures per contact exactly like the
    single-contact flow — one bad row never blocks the rest of the
    batch — and bulk Generate Email/DM still auto-advances each
    contact's current step / due date the same way single-contact
    generation does.
- **Open / review**: shows a contact's generated messages across
  **every** sequence step together (e.g. steps 1, 2, and 3 all
  visible at once), as a popup or separate page, with one-click copy
  of Subject (Email projects) and/or Body. This is not version
  history — per the overwrite-only rule below, there is only ever
  one current message per (contact, step); "Open" simply lists all
  of a contact's current per-step messages in one place.
- Designed around roughly 50–100 contacts per project; bulk actions
  run as a simple synchronous loop, not a background job queue.

### Generation & Review

- **Generate Email/DM** resolves the matching template for that
  contact (via conditions), substitutes CSV values and any saved AI
  field values, and saves the result. Running it again for the same
  contact/step **overwrites** the previous result — no version
  history is kept.
- If a required AI-sourced placeholder has no saved value yet,
  generation fails with a clear message telling the user to run
  **Generate AI Fields** (**Send Prompt** on the dashboard) first.
- The dashboard's **Open** action (see above) is the primary results
  view: per contact, every sequence step's current message with
  copy. The current step and due date are shown per contact and can
  be manually overridden at any time, independent of generation.

### Settings

- A single Gemini API key field. Stored as plain text in the local
  database — the app is single-user and local-only, so no
  encryption or per-user key management is built.
- The API client targets `gemini-3.1-flash-lite` as the primary
  model (the second-highest-capability model still on Google's free
  tier, as of the last check against ai.google.dev/pricing), with an
  automatic one-time fallback to `gemini-2.5-flash-lite` on a rate
  limit (HTTP 429) before surfacing an error. Gemini's free-tier
  model lineup changes every few months, so these model IDs should
  be re-verified against current Google docs before each
  implementation pass rather than assumed to stay correct.

## Scope

### In Scope

- Single local user, email/password auth (via the existing starter
  auth app).
- Email-type and LinkedIn-DM-type projects.
- CSV import with merge-only re-upload, multi-step sequences,
  condition-based template selection.
- Gemini-backed AI placeholder generation, configured per template,
  with an optional per-contact-per-step prompt override.
- A contact dashboard supporting bulk AI-field generation and bulk
  message generation, at a scale of roughly 50–100 contacts per
  project.
- Generated-message storage with open/copy, overwritten on
  regeneration.
- Manual, non-blocking due-date and step tracking.

### Out of Scope

- Actually sending any email or LinkedIn message — the app only
  generates text for the user to copy and send elsewhere.
- Multi-user accounts, teams, or per-user data isolation beyond what
  the starter's auth already provides.
- Any AI provider other than Gemini.
- Version history of generated messages — always overwrite, never
  keep multiple generations per contact/step. (The dashboard's
  "Open" action listing all of a contact's per-step messages
  together is not an exception to this — it's one current message
  per step, shown together.)
- Background/async job processing for bulk actions (no Celery or
  similar) — bulk dashboard actions run synchronously, which is
  acceptable at the app's target scale (roughly 50–100 contacts per
  project).
- Automated enforcement, reminders, or notifications tied to due
  dates.
- Production deployment concerns (HTTPS, hosting, outbound email
  delivery) — this runs on the local Django dev server.

## Success Criteria

1. A signed-up user can create one Email-type and one LinkedIn
   DM-type project, each with its own CSV import and sequence.
2. Uploading the same CSV twice adds only genuinely new contacts (by
   key column); no existing contact row is duplicated or altered.
3. A sequence step with three condition templates picks the correct
   template per contact based on CSV values, and falls back to the
   default template when no condition matches.
4. For a template with AI-sourced placeholders, running **Generate
   AI Fields** and then **Generate Email/DM** produces a complete
   message with every placeholder substituted (CSV and AI alike).
5. A failed Gemini call for one contact does not affect generation
   for any other contact, and can be retried from that same row —
   including when the call is part of a bulk Send Prompt action.
6. Regenerating a message for the same contact/step overwrites the
   previous result in place.
7. Deleting a project removes all of its sequence steps, templates,
   conditions, AI prompt configs, contact-level prompt overrides,
   contacts, and generated messages.
8. From a project's dashboard, a user can set a custom AI prompt for
   an individual contact at a specific step (leaving every other
   contact on the template's default prompt), bulk-select a group of
   contacts, run Send Prompt and then Generate Email/DM across that
   selection, and open any one contact to see all of their generated
   messages (across every step) together with one-click copy.
