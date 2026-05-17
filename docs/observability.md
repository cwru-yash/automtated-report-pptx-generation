# Observability

The report platform now records structured JSON events for both parent batches
and language-specific child jobs.

## Why there are two IDs

- `batch_id` answers: what happened across the entire multilingual request?
- `job_id` answers: what happened inside one language-specific run?

For example, one English + Portuguese request creates one `batch_id` and two
child `job_id` values.

## Where logs live

```text
logs/system.jsonl
logs/batches/<batch_id>.jsonl
logs/jobs/<job_id>.jsonl
```

The same event can appear in more than one file so you can debug from the whole
system view, the batch view, or the single-child view.

## API access

```bash
curl http://127.0.0.1:8000/api/v1/batches/<batch_id>/logs
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>/logs
```

The frontend exposes a `Batch Log` link and one `Log` link per language row.

## Event trail

A normal child job emits events such as:

```text
job.started
bundle.assembled
narrative.completed
artifact.written
job.completed
```

A batch wraps those child events with:

```text
batch.started
batch.completed
```

If something goes wrong, the logs capture explicit failure events, for example:

```text
artifact.failed
job.failed
job.exception
job.batch_exception
```

Each event includes UTC timestamp, batch/job IDs, wave ID, language,
template ID, and stage-specific details such as artifact type, path, warning
count, or exception metadata.

## Example failure

If PPT generation is requested with a missing template, the child job can still
finish with HTML output, but the log records an `artifact.failed` event like:

```json
{
  "event": "artifact.failed",
  "artifact_type": "pptx",
  "error_type": "KeyError",
  "error": "'Template not found: missing_template'"
}
```

That gives an operator a clear answer to what failed, where it failed, and why.
