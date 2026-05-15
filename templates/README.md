# Template Drop Zone

Put reusable PowerPoint masters in `templates/ppt/`.

Example:

```text
templates/ppt/client_cvc_master.pptx
templates/ppt/client_cvc_master.schema.json
```

The sidecar schema is optional, but recommended. Its `placeholders` should match
PowerPoint shape names that the renderer can fill:

```json
{
  "placeholders": [
    {"name": "exec_summary", "type": "text"},
    {"name": "methodology", "type": "text"},
    {"name": "brand_health", "type": "text"},
    {"name": "weak_links", "type": "text"},
    {"name": "takeaways", "type": "text"}
  ]
}
```

After adding a deck, restart the API and call `/api/v1/templates` to see the
template ID. Use `/api/v1/templates/{template_id}/inspect` to list slides,
shape names, text samples, and missing required placeholders.
