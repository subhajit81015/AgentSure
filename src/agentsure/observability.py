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
) -> None:
    resource = Resource.create(
        {
            "service.name": service_name,
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

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

