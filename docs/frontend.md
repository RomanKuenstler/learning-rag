# Frontend

## Stack

- React 18
- TypeScript
- Vite
- `react-router-dom`
- `react-markdown` with `remark-gfm`
- `rehype-sanitize`

## Step 7 Layout Structure

- `AppShell` owns the fixed top bar, persistent left sidebar, and main workspace.
- `Sidebar` keeps all existing chat, archive, preferences, help, and info actions while matching the reference spacing and menu treatment more closely.
- `ChatView` now uses a low-chrome conversation layout with full-width assistant messages, right-aligned user bubbles, a fixed bottom composer, and inline error banners.
- `LibraryPage` is split into a compact summary card and a table card, following the reference section rhythm.
- `PreferencesDialog` now uses a two-column tabbed modal structure instead of a simple top-tab strip so it matches the reference modal layout.

## Major Component Structure

- `Dialog` is the shared modal primitive. Step 7 added optional sizing and body/content class hooks so compact confirmations and wide tabbed panels can share the same implementation.
- `ChatInput` keeps existing send and attachment behavior, but its markup now follows the reference composer pattern: fixed dock, attachment chips, attach trigger, mode selector, and icon-style send button.
- `MessageBubble` keeps markdown, attachments, and sources working while using role-specific layout wrappers that mirror the reference message treatment.
- `SourcesPanel` now renders as a compact evidence popover with summary text, stacked source rows, and restrained metadata styling.
- `PreferencesDialog` and `LibraryPage` both rely on the shared section and table styling language introduced in Step 7.
- `FilterTables` is the shared Step 9 filter surface for both global preferences and chat-specific filter dialogs.
- `KsaPanel` is the Learning-page KSA surface for the 3-radar big-map, shared Dreyfus legend, and full initial assessment flow dialog.

## KSA Visualization Notes

- The KSA tab uses a custom SVG radar implementation instead of an external chart library to keep bundle size and styling control stable.
- The layout is desktop-first: one row with three equal chart cards (`Knowledge`, `Skills`, `Abilities`), each using the same Dreyfus 1-5 ring model.
- `Start Assessment` opens a multi-step assessment dialog:
  - phase 1 slider sieve
  - knowledge verification
  - skill simulations
  - timed ability tasks
- Completed assessments refresh the persisted KSA profile and redraw the existing radar charts without changing layout.

## Step 9 Filtering UI

- The Library page still lists embedded files, but its enable toggle now mirrors the authenticated user's global file filter state.
- `Preferences -> Filter` shows global tag and file tables with immediate toggle persistence.
- Each chat menu exposes a `Filter` action that opens a dialog with chat-scoped tag and file controls.
- Globally disabled tags and files are rendered as locked in chat scope so the precedence rules stay visible in the UI.

## Step 12 GPT UI

- The sidebar now has a `GPTs` section above the normal chat list.
- GPT rows open persistent GPT chats while normal chat rows still open normal chats.
- GPT row menus expose `Edit`, `Clear`, `Download`, and `Delete`.
- `+ New GPT` opens a full-width editor route without the main sidebar.
- The GPT editor keeps configuration on the left and a non-persistent preview chat on the right.
- Preview history is cleared locally whenever any GPT config field changes.
- Persistent GPT chats lock the header assistant-mode picker because mode comes from the GPT itself.

## Learning Node Sessions UI Shell

- Sidebar now includes a dedicated `Learning Nodes` section.
- Items are not normal chats and not GPT chats; they map to dedicated learning-node sessions.
- Each item shows status icon state:
  - blue dotted circle (`created`)
  - orange/yellow half-filled circle (`in_progress`)
  - green check-in-circle (`completed`)
- Each item menu includes: `Archive`, `Reset` (placeholder), `Download` (placeholder), `Delete` (soft-delete).
- Dedicated learning-node route added: `/learning/nodes/:sessionId`.
- Courses node Start/Continue now ensures a reusable session for that user/node and navigates to that route.
- Archive tab in Preferences now includes archived learning-node sessions alongside archived chats.

## Learning Node Page Rendering

- `LearningNodePage` now renders from real node + runtime package data instead of shell placeholders.
- Top-of-page uses node title/description and metadata tags (`type`, `chapter`, `branch`, `route`, required/optional).
- Rendered node types in this step:
  - `milestone`
  - `assessment_hook`
  - `quiz`
  - `practice`
  - `checkpoint`
  - `capstone`
- `learning_unit`
- `review`
- `assessment_hook` uses KSA drill-style question cards directly on the page (no manual topic input).
- `quiz` reuses existing option-card and textarea styles for single/multi choice + free-text questions.
- `practice` reuses existing textarea style and attachment-chip language, with split text/upload layout for upload tasks.
- `checkpoint`/`capstone` compose quiz + practice + assessment sections into one page layout.
- `learning_unit` and `review` now use a shared multi-step lesson shell:
  - start step (topics + planned steps)
  - package-driven lesson steps (`mini_topic_lessons` for `learning_unit`, `recap_structure.mini_recaps` for `review`)
  - top progress bar
  - scrollable content body
  - fixed action footer with disabled `Audio`, `Explain again`, and right-side `Back`/`Next` navigation
  - bottom lesson controls for like/dislike and `Sources` menu (same popover pattern as assistant messages)
  - placeholder orange dotted technical-term tooltip and dummy media support (image/video)
- `unlock_gate` is route-guarded away from page rendering and has no normal learning-session entry path.

## Styling Approach

- Styling remains centralized in `webui/src/styles/index.css`.
- Step 7 introduced shared design tokens in `:root` for palette, borders, radius, shadows, and transitions.
- The stylesheet is organized around shell, sidebar, chat, composer, dialogs, tables, and preferences patterns instead of one-off local overrides.
- Reference parity is achieved by rebuilding styles against the existing React structure instead of copying the reference implementation directly.

## Restyling Refactors

- Normalized message and composer markup so the reference spacing rules can be applied consistently.
- Expanded the shared `Dialog` component to support both wide and compact modal variants.
- Moved the preferences UI into a sidebar-tab modal layout.
- Unified button, popover, chip, and table styling across chat, library, and preferences so the UI reads as one design system.

## Local Run

```bash
cd webui
npm install
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000`.

## Course Editor UI

New route:

- `/courses/:courseId/edit`

Implemented page behavior:

- GPT-style editor shell header (`Back`, `Save`)
- attachment table above JSON editor (images/videos/downloadable files)
- `Add Attachments` button with multi-file upload
- inline raw JSON text editor (monospace + syntax pre-check)
- attachment reference diagnostics section (`missing` / `ambiguous`)

Courses table integration:

- row menu `Edit` now navigates to `/courses/:courseId/edit`

API calls used by the page:

- `getCourseEditor(courseId)`
- `saveCourseEditor(courseId, rawJson)`
- `uploadCourseAttachments(courseId, files)`

Notes:

- the page is JSON-first by design (no visual node/tree authoring in this phase)
- JSON should reference media by file name only; backend resolves the concrete MinIO path
