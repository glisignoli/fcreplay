from opentelemetry import trace
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor


from grpc import ssl_channel_credentials


class Tracing:
    """Tracing for fcreplay."""

    def __init__(self, endpoint, secure, headers):
        """Initalise tracing."""
        # Set up tracing
        resource = Resource(
            attributes={"service_name": "fcreplay"}
        )

        trace.set_tracer_provider(TracerProvider(resource=resource))

        # Setup the exporter
        hnyExporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=secure,
            credentials=ssl_channel_credentials(),
            headers=headers
        )

        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(hnyExporter))

        # auto-instrument outgoing requests
        RequestsInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())

    def instrumentor(self, app):
        """Start flask tracing."""
        FlaskInstrumentor().instrument_app(app)
