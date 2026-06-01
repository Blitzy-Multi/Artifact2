"""Centralized error handlers for the Flask application.

This module reproduces the original Node.js/Express error-handling middleware
(``(err, req, res, next)``) via Flask's centralized ``@app.errorhandler``
registrations (AAP s0.4.2, s0.4.3, s0.5.1 Group 2).

All handlers return a consistent JSON error envelope::

    {"error": {"code": <status>, "message": <reason>}}

FOUNDATION BASELINE: The original Node.js source is currently ABSENT from the
repository, so the exact envelope shape and the full set of handled status
codes are finalized 1:1 once the source is supplied. Until then this module
provides a clean, generic JSON envelope for the common HTTP errors and a
catch-all handler so that no error escapes as an HTML response.

Conventions (AAP s0.7): absolute imports only; no business logic beyond error
formatting; no hardcoded secrets.
"""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def _error_response(code: int, message: str) -> tuple[Response, int]:
    """Build the standard JSON error envelope and HTTP status tuple.

    The envelope shape ``{"error": {"code": <status>, "message": <reason>}}``
    is intentionally generic; it will be reconciled 1:1 with the original
    server's error responses once the Node.js source is supplied.
    """
    payload = {"error": {"code": code, "message": message}}
    return jsonify(payload), code


def register_error_handlers(app: Flask) -> None:
    """Attach centralized JSON error handlers to the Flask ``app``.

    Called by the application factory (``app/__init__.py``) as the final step
    of the request/response pipeline via
    ``from app.middleware.error_handlers import register_error_handlers``.

    Registers handlers for the most common HTTP errors (404, 405, 500), a
    generic :class:`werkzeug.exceptions.HTTPException` handler that preserves
    the originating status code, and a catch-all :class:`Exception` handler
    that guarantees a 500 JSON envelope (never an HTML stack trace) for
    unhandled errors.
    """

    @app.errorhandler(404)
    def handle_not_found(error: HTTPException):
        return _error_response(404, getattr(error, "description", "Not Found"))

    @app.errorhandler(405)
    def handle_method_not_allowed(error: HTTPException):
        return _error_response(
            405, getattr(error, "description", "Method Not Allowed")
        )

    @app.errorhandler(500)
    def handle_internal_server_error(error: Exception):
        # Log the real cause server-side; never leak internals to the client.
        logger.exception("Unhandled 500 error: %s", error)
        return _error_response(500, "Internal Server Error")

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        # Preserve the original status code/description for any other HTTP error
        # (400, 401, 403, 409, 422, etc.) using the same JSON envelope.
        code = error.code or 500
        message = error.description or error.name
        return _error_response(code, message)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        # Catch-all: ensure non-HTTP exceptions still return the JSON envelope.
        # Re-raise HTTPExceptions so their dedicated handlers above run instead.
        if isinstance(error, HTTPException):
            raise error
        logger.exception("Unhandled exception: %s", error)
        return _error_response(500, "Internal Server Error")
