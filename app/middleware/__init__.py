"""Middleware package for the Flask application.

Houses the request/response pipeline parity layer for the Node.js -> Flask port
(AAP s0.4.2, s0.4.3, s0.5.1 Group 2):

* :mod:`app.middleware.hooks` -- ``before_request`` / ``after_request`` handlers
  reproducing the original Express global middleware (``app.use(...)``).
* :mod:`app.middleware.error_handlers` -- centralized ``@app.errorhandler``
  registrations reproducing the original error-handling middleware
  (``(err, req, res, next)``).

The ``register_hooks`` and ``register_error_handlers`` callables are re-exported
here for convenience so the application factory can import them either from the
submodules directly or from the package. Absolute imports only (AAP s0.7).
"""

from __future__ import annotations

from app.middleware.error_handlers import register_error_handlers
from app.middleware.hooks import register_hooks

__all__ = ["register_hooks", "register_error_handlers"]
