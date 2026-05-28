# Report Deck Demo Workflow

## Reader And Goal

This guide is for an internal engineer or demo operator who needs to run the
current report-to-deck workflow locally and explain its safety boundaries.

After reading it, you should be able to start the app, create an editable deck
from a completed wave, optionally preview and accept an AI outline, edit the
deck, and export PPTX or semantic HTML.

## What The Workflow Does

The deck system starts from a completed analytical wave or report artifact. It
does not rerun the upstream analysis. It reads the completed data, builds a
validated evidence bundle, creates a deterministic deck plan, maps that plan
into editable recursive deck JSON, and saves the editable deck locally.

```text
completed wave/report
  -> read-only bundle assembly
  -> deterministic findings extraction
  -> evidence-validated deck plan
  -> editable deck document
  -> local deck project
  -> editor, PPTX export, HTML preview
```

The important product promise is simple: the deck should explain the findings
that already exist. It should not invent findings, numbers, or charts.

## Deterministic Deck Flow

The deterministic flow is the default demo path.

1. The user enters a completed wave ID.
2. The backend loads the wave data through the configured provider.
3. The bundle assembler builds the analysis bundle.
4. The finding extractor blocks weak inputs, such as no gold rows or no
   completed analysis results.
5. The slide planner creates an evidence-backed deck plan.
6. The layout mapper creates editable recursive deck JSON.
7. The local deck repository persists the editable deck.
8. The editor opens the persisted deck by ID.

This path is deterministic-first. It works without LLM credentials.

## AI-Assisted Outline Flow

The optional AI flow only helps with outline planning.

```text
validated findings context
  -> AI outline suggestion
  -> schema validation
  -> evidence-ref validation
  -> human review
  -> accept outline
  -> deterministic deck plan and deck document
```

The AI may suggest:

- deck title
- objective
- audience
- slide order
- slide title
- slide purpose
- key message
- evidence references
- suggested visual type

The AI does not generate editable deck blocks. It does not generate arbitrary
recursive deck JSON. It does not directly persist a deck.

When a user accepts an AI outline, the backend revalidates the submitted
outline, checks evidence references against the extracted findings context, and
then uses the deterministic planner and mapper path to create the deck project.

## Why AI Only Controls The Outline

Recursive deck JSON is an execution format. It drives editing, autosave,
preview, and export. Letting AI directly create that structure would increase
the risk of malformed blocks, invented chart references, unsupported numeric
claims, and decks that render differently across frontend and server exports.

The safer boundary is:

- AI can suggest a story outline.
- The backend validates the outline.
- The backend owns deck plan generation.
- The backend owns editable deck JSON generation.
- Evidence validation runs before persistence.

This gives the user AI assistance without making AI the source of truth.

## Local Commands

Install backend dependencies:

```bash
poetry install
```

Install and build the editor:

```bash
cd frontend
npm install
npm run build
cd ..
```

Start the backend:

```bash
poetry run uvicorn app.main:app --reload
```

Check basic app health:

```bash
curl http://127.0.0.1:8000/health
```

Check deck readiness:

```bash
curl http://127.0.0.1:8000/api/v1/decks/readiness
```

Run backend checks:

```bash
poetry run python -m compileall app/deck app/renderers tests
poetry run pytest tests/test_deck_routes.py tests/test_deck_layout_schema.py tests/test_report_deck_builder.py
```

Run frontend checks:

```bash
cd frontend
npm test
npm run build
```

## Demo Steps

1. Start the backend.
2. Open the report console at `http://127.0.0.1:8000/`.
3. Confirm deck readiness at `http://127.0.0.1:8000/api/v1/decks/readiness`.
4. Open the deck editor at `http://127.0.0.1:8000/decks/editor`.
5. Enter a completed wave ID.
6. Click `Create Editable Deck` for the deterministic path.
7. Confirm the success message shows the created deck ID and open-deck link.
8. Edit a title, paragraph, or bullet in the deck editor.
9. Wait for autosave to return to `saved`.
10. Refresh the editor URL and confirm the latest saved deck reloads.
11. Click `Export PPT` to download the semantic PPTX export.
12. Click `HTML Preview` to open the semantic HTML preview.

For the optional AI outline path:

1. Enter a completed wave ID.
2. Click `Generate AI Outline`.
3. Review the returned outline cards.
4. Confirm evidence refs are present on non-title slides when possible.
5. Click `Create Deck from AI Outline`.
6. Confirm the created deck opens in the same editor and can be saved/exported.

If AI outline credentials are not configured, the outline request should show a
visible provider-disabled message. The deterministic deck path should still work.

## Readiness Endpoint

The readiness endpoint is a local demo check. It does not call live AI and does
not query production Supabase, BigQuery, or GCS.

Expected shape:

```json
{
  "deck_routes": "ok",
  "local_persistence": "ok",
  "pptx_export": "ok",
  "html_preview": "ok",
  "ai_outline": "disabled",
  "details": {}
}
```

`ai_outline` reports `enabled` only when local configuration appears sufficient
to attempt AI outline generation. It does not prove that a live provider call
will succeed.

`pptx_export` can report `error` if the PowerPoint dependency or local template
is missing. The `details` object should explain the failure.

## Known Limitations

- AI outline generation is optional and may be disabled in local development.
- AI output is preview-only until a human explicitly accepts it.
- The accepted outline still goes through deterministic mapping, so layout
  choices are intentionally conservative.
- PPTX export is semantic, not visually polished.
- HTML preview is semantic and readable, not a final branded report.
- Editable deck persistence is local/app-owned for the MVP.
- No production Supabase, BigQuery, or GCS writes happen in this workflow.
- The editor has basic text editing and autosave, not a full presentation design
  suite.

## Demo Failure Cases To Show

- A bad wave with no gold rows should return a visible 422 instead of a fake deck.
- A wave with empty completed analysis results should return a visible 422.
- An AI outline with an invalid evidence ref should be rejected on accept.
- Missing AI provider config should show a visible disabled-provider message.
- Missing PPT template support should show an export/readiness error instead of
  failing silently.
