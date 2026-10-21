# Architecture Context

## Stack

| Layer         | Technology                                                                 | Role                                                                 |
| ------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Framework     | Django 5 (Python), built on `andyjud/django-starter` (`_core`, `a_home`, `a_users`) | Server-rendered app, routing, ORM, base auth scaffold                 |
| Frontend      | Django templates + htmx for all server interactions                         | Server-driven interactivity, no SPA framework, no JS build step       |
| Client JS     | Minimal vanilla JS, scoped to one place only: the drag-and-drop placeholder editor | Lets CSV column chips be dragged into a contentEditable Subject/Body field |
| Styling       | Plain CSS shipped with the starter's `static/` folder                       | No Tailwind/build pipeline needed                                     |
| Auth          | Starter's `a_users` CustomUser app (email/password + email confirmation)    | Login/signup for the single local user                                |
| Database      | SQLite via Django ORM                                                       | All app data — projects, contacts, templates, generated messages      |
| AI Provider   | Google Gemini free-tier API (key from https://aistudio.google.com/app/api-keys), called server-side from Django | Fills AI-sourced placeholders                                         |
| CSV Handling  | Python stdlib `csv` module                                                  | Parses uploaded CSV into contact rows; no extra dependency needed     |

## System Boundaries

- `_core/` — Django project settings, root URLConf, WSGI entry; the
  single place that reads the Gemini key (from the Settings model)
  and exposes a shared `PROJECT_TITLE`.
- `a_home/` — Starter's existing landing views, repurposed as the
  post-login dashboard entry point (links into the project list).
- `a_users/` — Starter's CustomUser model and signup/login/email-
  confirmation flows, unmodified except for branding text.
- `a_projects/` — `Project` model (name, type, `key_column`,
  cached `csv_columns`), project CRUD, CSV upload + merge-import
  logic, and the single-row `Settings` model (Gemini API key).
- `a_sequences/` — `SequenceStep`, `Template`, `TemplateCondition`,
  and `AIPromptConfig` models; sequence/template/condition CRUD; the
  shared placeholder-parsing utility (used by both templates and AI
  prompts); the drag-and-drop template editor UI.
- `a_contacts/` — `Contact` model (project FK, JSON `data` field
  holding every CSV column for that row, `current_step`,
  `next_due_date`); contacts list/table view; manual step/due-date
  edit.
- `a_generation/` — `GeneratedAIField` and `GeneratedMessage`
  models; the Gemini client wrapper; the "Generate AI Fields" and
  "Generate Email/DM" views; the condition-matching / template-
  resolution logic; the results/review views (open, copy).

## Storage Model

- **Database (SQLite)**: everything the app knows — projects,
  sequence steps, templates, conditions, AI prompt configs,
  contacts (CSV rows stored as JSON), generated AI field values,
  generated messages, and the Gemini API key.
- **No blob/file storage**: an uploaded CSV is parsed on upload and
  then discarded as a file — only the resulting contact rows are
  persisted in the database. Nothing is written to disk outside the
  database.

## Auth and Access Model

- Every user signs in via the starter's CustomUser email/password
  flow (including its email-confirmation step, as shipped).
- The app is built for a single local user; there is no
  organization/team concept.
- Every `Project` belongs to the logged-in user; every
  `SequenceStep`, `Template`, `TemplateCondition`, `AIPromptConfig`,
  `Contact`, `GeneratedAIField`, and `GeneratedMessage` belongs
  (directly or transitively, via FK chain) to exactly one `Project`.
  View-level `request.user` ownership checks exist as defense in
  depth, not as a multi-tenant feature.

## Invariants

1. A `SequenceStep` always has exactly one condition-less (default)
   `Template`; template resolution for a contact must never fail to
   find a template to use.
2. Condition templates on a step are evaluated in explicit priority
   order (ascending `order`); the first template whose conditions
   all match wins. Conditions within one template are always ANDed,
   never ORed.
3. A placeholder found in a Subject/Body is **CSV-sourced** if it
   matches (case-insensitive, trimmed) a column in the project's
   `csv_columns`; otherwise it is **AI-sourced** and must be covered
   by that template's `AIPromptConfig` output tags, or generation
   fails with a clear, placeholder-specific error telling the user
   to configure or run AI generation first.
4. CSV re-import never mutates or removes an existing `Contact` row
   — it only inserts rows whose key-column value isn't already
   present for that project.
5. "Generate AI Fields" and "Generate Email/DM" are always two
   separate actions; Gemini is never called as a side effect of
   building the final message — only previously saved
   `GeneratedAIField` values are used at that point.
6. Regenerating a message (AI fields or the final email/DM) always
   **overwrites** the prior saved value for that exact (contact,
   step, placeholder-or-message) — no history/versioning is kept
   anywhere in the system.
7. Deleting a `Project` cascades to delete every `SequenceStep`,
   `Template`, `TemplateCondition`, `AIPromptConfig`, `Contact`,
   `GeneratedAIField`, and `GeneratedMessage` that belongs to it —
   deleting a project must never leave orphaned rows.
8. A Gemini call failure for one contact/row is isolated: it is
   caught, stored as an error state on that row, and surfaced with a
   retry action; it never aborts or blocks generation for any other
   contact in the same batch.
