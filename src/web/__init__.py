"""
Web Dashboard Package

Provides a Flask-based REST API and HTML dashboard for the ScreenerIII
commodity trading scanner platform.

Quick start::

    from src.web import create_app, ScreenerApp

    # Option A: factory function (recommended for WSGI servers)
    app = create_app(debug=True)
    app.run()

    # Option B: class-based
    screener = ScreenerApp(debug=True)
    screener.run(host="0.0.0.0", port=5000)

Author: ScreenerIII
License: MIT
"""

from .app import (
    ScreenerApp,
    ResponseFormatter,
    SortOrder,
    create_app,
    API_VERSION,
    API_PREFIX,
    FLASK_AVAILABLE,
)

__all__ = [
    "ScreenerApp",
    "ResponseFormatter",
    "SortOrder",
    "create_app",
    "API_VERSION",
    "API_PREFIX",
    "FLASK_AVAILABLE",
]
