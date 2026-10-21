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

## Goals

1. Let one person run multiple outreach campaigns (email or LinkedIn
   DM), each with its own CSV-sourced contact list and multi-step
   sequence of templates.
2. Support conditional template selection per sequence step so the
   right message variant is chosen automatically based on CSV data.
3. Let AI (Gemini) fill template placeholders that cannot be sourced
   from the CSV, driven by a per-template configurable prompt, with
   no code changes required to add a new AI-backed campaign.
4. Keep every generated email/DM retrievable and copyable until the
   user explicitly deletes the project.

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
   placeholders don't match a CSV column, write a prompt that
   outputs those placeholder values inside named tags; the prompt
   itself may reference CSV columns and/or one-off manual-input
   fields.
8. Generate, per contact:
   a. If the resolved template needs AI-sourced placeholders, fill
      any manual-input boxes and click **Generate AI Fields**.
   b. Click **Generate Email/DM** — the app substitutes CSV values
      and any saved AI field values into the matching template and
      saves the result.
9. Review & Copy → open any generated message in the results view
   and copy the Subject and/or Body.
10. Track → see each contact's current step and due date; manually
    advance the step or change the due date at any time — nothing
    about due dates is enforced or automated beyond suggesting the
    next date.
11. Delete Project → removes the project and everything that
    belongs to it (sequence, templates, contacts, generated
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

### AI-Generated Placeholders

- AI generation is configured **per template**: one prompt can
  produce one or more named output values in a single Gemini call.
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
  formatting instructions themselves.
- **Generate AI Fields** is a separate, manual, per-contact,
  per-step action that must be run (when needed) *before*
  **Generate Email/DM**. The two are never combined into one click.
- The Gemini API key lives on the Settings page (Gemini free tier:
  https://aistudio.google.com/app/api-keys).
- A failed Gemini call (bad key, rate limit, quota) shows a clear
  inline error on that specific contact/row only, with a retry
  action; it never blocks or fails generation for any other contact.

### Generation & Review

- **Generate Email/DM** resolves the matching template for that
  contact (via conditions), substitutes CSV values and any saved AI
  field values, and saves the result. Running it again for the same
  contact/step **overwrites** the previous result — no version
  history is kept.
- If a required AI-sourced placeholder has no saved value yet,
  generation fails with a clear message telling the user to run
  **Generate AI Fields** first.
- A results view lists every contact × sequence step with an
  Open/Copy action showing the Subject (Email only) and Body.
- The current step and due date are shown per contact and can be
  manually overridden at any time, independent of generation.

### Settings

- A single Gemini API key field. Stored as plain text in the local
  database — the app is single-user and local-only, so no
  encryption or per-user key management is built.

## Scope

### In Scope

- Single local user, email/password auth (via the existing starter
  auth app).
- Email-type and LinkedIn-DM-type projects.
- CSV import with merge-only re-upload, multi-step sequences,
  condition-based template selection.
- Gemini-backed AI placeholder generation, configured per template.
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
  keep multiple generations per contact/step.
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
   for any other contact, and can be retried from that same row.
6. Regenerating a message for the same contact/step overwrites the
   previous result in place.
7. Deleting a project removes all of its sequence steps, templates,
   conditions, AI prompt configs, contacts, and generated messages.
