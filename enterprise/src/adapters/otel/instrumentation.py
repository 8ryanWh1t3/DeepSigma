"""Auto-instrumentation utilities for DeepSigma connectors and adapters.

Provides decorators and a base mixin that wrap adapter methods with OTel
spans and W3C trace-context propagation so every connector call is visible
in the span tree without manual instrumentation per adapter.

Usage:

    from adapters.otel.instrumentation import traced

    class SharePointConnector:
        @traced("sharepoint", operation="list_items")
        def list_items(self, site_id: str) -> list:
            ...

Or via the mixin:

    class SharePointConnector(InstrumentedConnector):
        connector_name = "sharepoint"
        ...
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import context, trace
    from opentelemetry.trace import StatusCode
    from opentelemetry.trace.propagation import get_current_span

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

# ── Span constants (registered in spans.py via prefix convention) ────
SPAN_CONNECTOR_PREFIX = "connector"  # connector.{name}.{operation}
ATTR_CONNECTOR_NAME = "deepsigma.connector.name"
ATTR_CONNECTOR_OP = "deepsigma.connector.operation"
ATTR_CONNECTOR_DURATION_MS = "deepsigma.connector.duration_ms"


def _get_tracer() -> Any:
    """Return the global tracer if OTel is available."""
    if not HAS_OTEL:
        return None
    try:
        return trace.get_tracer("sigma-overwatch")
    except Exception:
        return None


def traced(
    connector_name: str,
    operation: Optional[str] = None,
) -> Callable:
    """Decorator that wraps a method in an OTel span with connector attributes.

    Args:
        connector_name: Logical connector name (e.g. "sharepoint", "snowflake").
        operation: Operation label. Defaults to the decorated function name.
    """
    def decorator(fn: Callable) -> Callable:
        op = operation or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = _get_tracer()
            if tracer is None:
                return fn(*args, **kwargs)

            span_name = f"{SPAN_CONNECTOR_PREFIX}.{connector_name}.{op}"
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute(ATTR_CONNECTOR_NAME, connector_name)
                span.set_attribute(ATTR_CONNECTOR_OP, op)
                t0 = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as exc:
                    span.set_status(StatusCode.ERROR, str(exc))
                    raise
                finally:
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    span.set_attribute(ATTR_CONNECTOR_DURATION_MS, elapsed_ms)

        return wrapper
    return decorator


class InstrumentedConnector:
    """Mixin that auto-instruments public methods with OTel spans.

    Subclasses set ``connector_name`` as a class attribute. All public
    methods (not starting with ``_``) are wrapped automatically on
    first instantiation.
    """

    connector_name: str = "unknown"
    _instrumented: bool = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not HAS_OTEL:
            return
        for attr_name in list(vars(cls)):
            if attr_name.startswith("_"):
                continue
            method = getattr(cls, attr_name)
            if callable(method):
                setattr(cls, attr_name, traced(cls.connector_name, attr_name)(method))


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """Inject W3C traceparent into outbound HTTP headers.

    Call this before making an HTTP request from a connector to propagate
    the current trace context to the downstream service.
    """
    if not HAS_OTEL:
        return headers
    try:
        from opentelemetry.propagate import inject
        inject(headers)
    except Exception:
        logger.debug("Failed to inject trace context", exc_info=True)
    return headers


def extract_trace_context(headers: dict[str, str]) -> Any:
    """Extract W3C traceparent from inbound HTTP headers.

    Call this at adapter entry points (e.g. MCP server, webhook handler)
    to attach the incoming trace context to the current span.
    """
    if not HAS_OTEL:
        return None
    try:
        from opentelemetry.propagate import extract
        return extract(headers)
    except Exception:
        logger.debug("Failed to extract trace context", exc_info=True)
        return None
