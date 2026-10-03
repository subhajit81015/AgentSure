from collections.abc import Callable
from functools import wraps
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)


def configure_otel(
    service_name: str,
    otlp_endpoint: str | None = None,
    enable_exporter: bool = True,
) -> None:
    resource = Resource.create(
        {
            "service.name": service_name,
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

    if enable_exporter:
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                provider.add_span_processor(
                    BatchSpanProcessor(
                        OTLPSpanExporter(
                            endpoint=otlp_endpoint,
                            insecure=True,
                        )
                    )
                )
            except ImportError as exc:
                raise RuntimeError(
                    "Install opentelemetry-exporter-otlp "
                    "to use OTLP tracing."
                ) from exc
        else:
            provider.add_span_processor(
                BatchSpanProcessor(
                    ConsoleSpanExporter()
                )
            )

    trace.set_tracer_provider(provider)


def tracer():
    return trace.get_tracer("agentsure")


def traced_agent_run(func: Callable[..., Any]) -> Callable[..., Any]:
    """Trace one complete agent execution."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        current_tracer = tracer()

        with current_tracer.start_as_current_span(
            "agentsure.agent.run"
        ) as span:
            span.set_attribute(
                "agent.method",
                func.__qualname__,
            )

            try:
                result = func(*args, **kwargs)
                span.set_attribute(
                    "agent.status",
                    "success",
                )
                return result
            except Exception as exc:
                span.set_attribute(
                    "agent.status",
                    "error",
                )
                span.record_exception(exc)
                raise

    return wrapper
