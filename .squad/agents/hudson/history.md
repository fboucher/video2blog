# Hudson — History

## Project Context
- **Project:** video2blog
- **Stack:** Jinja2, HTML5, CSS3, vanilla JavaScript, Flask template rendering
- **User:** fboucher
- **Mission:** Build UI for Gemini migration (issues #23, #26)
- **Base branch:** dev
- **Feature branches:** squad/23, squad/26 (branched from dev)

## Architecture Overview

### Frontend Structure
- **`templates/`** — All Jinja2 templates (base.html, form.html, status panels, modals)
- **`static/css/`** — Stylesheets (normalize.css, layout.css, components.css)
- **`static/js/`** — JavaScript modules (api-client.js, ui-controller.js, form-handler.js)

### Key Templates & Components
- **`base.html`** — Base layout with navigation, footer, static assets
- **`upload.html`** — File upload form with progress indicator (for #23)
- **`library.html`** — Video library grid, status indicators, cache info (for #23)
- **`qa.html`** — Question/answer conversation panel (for #23, #26)
- **`url-video.html`** — URL input form, frame preview, Q&A (for #26)

### Issue Map & Frontend Scope

| Issue | Title | Hudson Scope |
|-------|-------|--------------|
| #23 | Local video upload + file caching | Upload form, library status panel, cache indicator |
| #26 | URL video Q&A without download | URL input form, frame preview, Q&A display |

## Flask Template Patterns
- Use `render_template()` with context dicts from routes
- Jinja2 loops for dynamic content (video lists, Q&A history)
- Form validation with HTML5 attributes + AJAX fallback
- Loading states via CSS classes and JavaScript toggles

## AJAX Integration Strategy
- Fetch API for POST (upload, Q&A), GET (library status, frames)
- Error responses handled with toast notifications
- Loading spinners on long-running requests
- Graceful fallback if JavaScript disabled

## CSS Conventions
- Mobile-first responsive design
- CSS Grid for layouts, Flexbox for components
- No CSS frameworks (vanilla CSS only)
- Semantic color naming (--color-primary, --color-error, etc.)

## JavaScript Conventions
- Vanilla JS (no jQuery, no React)
- Event listeners scoped to specific elements
- Separation of concerns (api module, ui module, form module)
- Consistent error handling for network failures

## Learnings
- Initial setup complete. Ready for issue #23 template implementation.
