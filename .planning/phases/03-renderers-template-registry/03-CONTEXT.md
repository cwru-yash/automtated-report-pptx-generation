# Phase 3 Context: Renderers & Template Registry

**Gathered:** 2026-05-03
**Status:** Ready for planning
**Source:** discuss-phase conversation

<domain>
## Phase Boundary

Build three independent renderers (PPT, HTML, PDF) that consume an `AnalysisBundle` + generated narrative sections and produce publication-ready output. Establish a Template Registry that maps template IDs to `.pptx` / Jinja2 template files with validated placeholder schemas.
</domain>

<decisions>
## Implementation Decisions

### PPT Renderer
- The developer already has existing `.pptx` master template files — do NOT generate sample templates, instead integrate with what exists.
- Use `python-pptx` to locate named placeholders (e.g., `nps_chart_image`, `exec_summary_text`) and inject content blocks and chart images.
- Placeholder names must exactly match the schema registered in the Template Registry.

### HTML Renderer
- Default mode: **Branded** — styled report matching Jinja2 templates the team already has. Use those existing HTML templates as the base.
- Also support a **Minimal** mode (clean, no-frills CSS) selectable via a flag/parameter — useful for downstream PDF conversion and testing.
- Renderer accepts `template_id` to select the right Jinja2 template from the registry.

### PDF Renderer
- Convert HTML output to PDF via `WeasyPrint`.
- PDF renderer is a thin wrapper: call HTML renderer first, then pipe the HTML string into WeasyPrint.
- No separate PDF template — PDF is always derived from HTML.

### Template Registry
- Central registry in `app/templates/registry.py` that maps `template_id → TemplateSpec`.
- `TemplateSpec` holds: file path (.pptx or .html), type (ppt | html), and a dict of required placeholder names with their types (text | image | number).
- Registry validates that all required placeholders exist in the template file at load time — fail loud if a placeholder is missing.

### Locale System
- Create **stub** locale files: `locales/en-US.json` and `locales/pt-BR.json`.
- Stubs contain the full set of static label keys (section headers, date formats, footer text, confidentiality notice) with English as the default and Portuguese as `"[TRANSLATE: ...]"` markers.
- The company has a pt-BR PPT deck but it's client-specific and not generalized yet — do NOT attempt to extract translations from it now.
- Locale files are loaded by Jinja2 templates as a context variable `{{ labels }}`.

### Renderer Split
- Plans are split: PPT Renderer (03-01), HTML Renderer (03-02), PDF Renderer + Locale Stubs (03-03).
- Each plan can be executed and tested independently.

### Agent's Discretion
- CSS design details for the minimal HTML mode.
- Exact Jinja2 template block structure (use `{% block %}` pattern for overrides).
- WeasyPrint page size and margin defaults (A4 is fine).
- How the Template Registry is initialized at FastAPI startup (lifespan hook).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 outputs (what renderers consume)
- `app/bundle/schema.py` — `AnalysisBundle` model (the data contract)
- `app/narrative/graph.py` — `run_narrative_engine()` output structure (sections dict)

### Project config
- `app/config.py` — Settings model (add TEMPLATES_DIR, LOCALES_DIR paths)
- `app/main.py` — FastAPI app + lifespan (where Template Registry initializes)

### Planning
- `.planning/ROADMAP.md` — Phase 3 success criteria
- `.planning/REQUIREMENTS.md` — REQ-03, REQ-04, REQ-05, REQ-06
</canonical_refs>

<specifics>
## Specific Ideas

- Locale key set (minimum): `exec_summary`, `methodology`, `brand_health`, `weak_links`, `takeaways`, `confidential`, `page`, `of`, `prepared_by`, `date_format`.
- Template Registry should expose `get_template(template_id)` and `list_templates()` functions.
- PPT renderer should raise a typed `PlaceholderNotFoundError` rather than silently skipping.
- HTML renderer returns a string (not a file) so the PDF renderer can pipe it directly.
</specifics>

<deferred>
## Deferred Ideas

- Migrating the client-specific pt-BR PPT deck into the generic template system — deferred until the pattern is proven with en-US.
- es-MX, ko-KR, zh-CN locale files — deferred to Phase 7.
- Template upload API (accepting new .pptx files via HTTP) — deferred to Phase 7.
- Template guardrails (overflow, missing assets, wrong-brand logos) — deferred to Phase 8.
</deferred>

---
*Phase: 03-renderers-template-registry*
*Context gathered: 2026-05-03 via discuss-phase*
