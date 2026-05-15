import os

os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")
os.environ.setdefault("OTEL_PYTHON_CONTEXT", "contextvars_context")

try:
    import importlib_metadata

    _otel_entrypoints = importlib_metadata.EntryPoints(
        [
            importlib_metadata.EntryPoint(
                name="contextvars_context",
                value="opentelemetry.context.contextvars_context:ContextVarsRuntimeContext",
                group="opentelemetry_context",
            ),
            importlib_metadata.EntryPoint(
                name="tracecontext",
                value="opentelemetry.trace.propagation.tracecontext:TraceContextTextMapPropagator",
                group="opentelemetry_propagator",
            ),
            importlib_metadata.EntryPoint(
                name="baggage",
                value="opentelemetry.baggage.propagation:W3CBaggagePropagator",
                group="opentelemetry_propagator",
            ),
            importlib_metadata.EntryPoint(
                name="default_tracer_provider",
                value="opentelemetry.trace:NoOpTracerProvider",
                group="opentelemetry_tracer_provider",
            ),
            importlib_metadata.EntryPoint(
                name="default_meter_provider",
                value="opentelemetry.metrics:NoOpMeterProvider",
                group="opentelemetry_meter_provider",
            ),
        ]
    )

    def _fast_entry_points(**params):
        if params:
            return _otel_entrypoints.select(**params)
        return _otel_entrypoints

    importlib_metadata.entry_points = _fast_entry_points
except Exception:
    pass
