from fcreplay.site.create_app import create_app
from fcreplay.site.site_config import DevConfig, ProdConfig
from flask.helpers import get_debug_flag, get_env

if get_debug_flag() or get_env != "production":
    CONFIG = DevConfig
else:
    CONFIG = ProdConfig

app = create_app(CONFIG)

if CONFIG.config.opentelemetry_config['enabled']:
    from fcreplay.site.tracing import Tracing

    print("OpenTelemetry enabled")
    print(f"Endpoint: {CONFIG.config.opentelemetry_config['endpoint']}")
    print(f"Headers: {CONFIG.config.opentelemetry_config['headers']}")
    print(f"Secure: {CONFIG.config.opentelemetry_config['secure']}")

    t = Tracing(
        endpoint=CONFIG.config.opentelemetry_config['endpoint'],
        secure=CONFIG.config.opentelemetry_config['secure'],
        headers=CONFIG.config.opentelemetry_config['headers']
    )

    print("Starting open telemetry instrumentation")
    t.instrumentor(app)
