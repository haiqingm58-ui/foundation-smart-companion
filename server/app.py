"""Production ASGI entry point.

Database migrations and legacy imports are intentionally run by deployment
before this module is started, keeping application startup deterministic.
"""

from .application.main import create_app


app = create_app()
