"""Request lifecycle hooks for the Flask application.

This module reproduces the original Node.js/Express global middleware pipeline
(``app.use(...)``) via Flask ``before_request`` / ``after_request`` handlers
(AAP s0.4.2, s0.4.3, s0.5.1 Group 2).

FOUNDATION BASELINE: The original Node.js source is currently ABSENT from the
repository. Per the parity mandate (AAP s0.6.2/s0.7) this module therefore keeps
the pipeline MINIMAL and non-fabricating:

* ``before_request`` is effectively a no-op (it only emits an optional debug
  log line); it does NOT implement authentication/session logic, because there
  is no source to mirror yet.
* ``after_request`` returns the response unmodified (optionally emitting a basic
  request log line via the stdlib :mod:`logging` module).

CORS is intentionally NOT handled here: the application factory binds
``Flask-Cors`` (``cors.init_app(app)``) before these hooks run, so CORS headers
and preflight handling are already covered.

When the original source is supplied, the concrete global-middleware behaviors
(authentication, request-context attachment, custom logging format, any CORS
preflight Flask-Cors does not cover, etc.) are added here 1:1 in the original
pipeline order.

Conventions (AAP s0.7): absolute imports only; no hardcoded secrets; no business
logic beyond request lifecycle handling.
"""

from __future__ import annotations

import logging

from flask import Flask, Response, request

logger = logging.getLogger(__name__)


def register_hooks(app: Flask) -> None:
    """Attach request lifecycle hooks to the Flask ``app``.

    Called by the application factory (``app/__init__.py``) via
    ``from app.middleware.hooks import register_hooks`` immediately after
    blueprint registration and immediately before the error handlers, matching
    the original Express global-middleware position in the pipeline.
    """

    @app.before_request
    def _before_request() -> None:
        # No-op baseline. Emits a debug log line only; performs no auth/session
        # work (no source to mirror yet). Returning None lets the request
        # proceed to the matched view unchanged.
        logger.debug("--> %s %s", request.method, request.path)
        return None

    @app.after_request
    def _after_request(response: Response) -> Response:
        # Return the response unmodified. Emits a basic request log line using
        # the stdlib logging module; adds no headers or body transformations.
        logger.info(
            "%s %s -> %s", request.method, request.path, response.status_code
        )
        return response
