# Demo Dry Run

Use this flow before recording a video demo.

## 1. First rehearsal: use the known-good demo master

Keep the API running, then confirm the service and template are available:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/templates/demo_master/inspect
```

Run the deterministic fallback path first so you can validate the render pipeline
without depending on LLM credentials:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "wave_id": "demo-wave",
    "language": "en-US",
    "template_id": "demo_master",
    "use_llm": false,
    "include_pdf": true
  }'
```

Check that the response includes paths for `html`, `pptx`, and `pdf`, then open
the generated files in `artifacts/`.

## 2. Prepare one client deck for automation

The client decks in `templates/ppt/` are finished reports today, not automation
masters yet. Pick one deck to convert into a first reusable master. For the
quickest first pass, start with the smallest file:

```text
templates/ppt/Robot Vacuum Market Report Q3 2025.pptx
```

Save a copy such as:

```text
templates/ppt/client_cvc_master.pptx
templates/ppt/client_cvc_master.schema.json
```

Use this schema:

```json
{
  "placeholders": [
    { "name": "exec_summary", "type": "text" },
    { "name": "methodology", "type": "text" },
    { "name": "brand_health", "type": "text" },
    { "name": "weak_links", "type": "text" },
    { "name": "takeaways", "type": "text" }
  ]
}
```

In PowerPoint, open the Selection Pane and rename the five text boxes you want
Codex to fill to those exact names.

## 3. Validate the client master

Restart the API so newly added decks are registered, then inspect the new master:

```bash
curl http://127.0.0.1:8000/api/v1/templates
curl http://127.0.0.1:8000/api/v1/templates/client_cvc_master/inspect
```

Do not continue until `missing_placeholders` is empty.

## 4. Run the client-template rehearsal

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "wave_id": "demo-wave",
    "language": "en-US",
    "template_id": "client_cvc_master",
    "use_llm": false,
    "include_pdf": true
  }'
```

Open the resulting PPTX and verify:

1. The right five shapes were replaced.
2. Text does not overflow or wrap badly.
3. The untouched visual system of the client deck still looks intact.
4. PDF and HTML artifacts also render.

## 5. Final recording rehearsal: require real LLM output

Only after the render path is stable, run the real LLM version:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "wave_id": "demo-wave",
    "language": "pt-BR",
    "template_id": "client_cvc_master",
    "use_llm": true,
    "require_llm": true,
    "include_pdf": true
  }'
```

For the recording take, use `require_llm: true`. If credentials are broken, the
job should fail visibly instead of silently falling back to placeholder copy.
