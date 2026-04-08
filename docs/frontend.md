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
- `KsaPanel` is the Learning-page KSA surface for the 3-radar big-map, baseline messaging, and placeholder assessment dialog shell.

## KSA Visualization Notes

- The KSA tab uses a custom SVG radar implementation instead of an external chart library to keep bundle size and styling control stable.
- The layout is desktop-first: one row with three equal chart cards (`Knowledge`, `Skills`, `Abilities`), each using the same Dreyfus 1-5 ring model.
- `Start Assessment` opens a modal that deliberately mirrors the diagnostic dialog structure while staying placeholder-only in this step.

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
