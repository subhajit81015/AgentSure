from agentsure.observability import configure_otel, tracer


def test_configure_otel_creates_service_tracer():
    configure_otel(
        "agentsure-test",
        enable_exporter=False,
    )

    current_tracer = tracer()

    with current_tracer.start_as_current_span("test-span") as span:
        span.set_attribute("test.attribute", "ok")
        assert span.is_recording()
