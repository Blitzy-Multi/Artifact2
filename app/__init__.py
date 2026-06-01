"""Application factory (composition root) for the Artifact2 Flask application.

This module is the single composition root of a Python 3 + Flask application
that re-implements an existing Node.js (Express) server with **behavioral
parity** (AAP Sections 0.1 and 0.4.2). It maps the original
``app.js`` / ``server.js`` / ``index.js`` bootstrap (AAP Section 0.4.3): where
the Node entrypoint constructed an Express ``app``, wired global middleware,
mounted routers, and called ``app.listen(...)``, this module exposes the
:func:`create_app` factory that constructs a configured :class:`flask.Flask`
instance and hands it back to its callers (``wsgi.py`` under gunicorn, and the
pytest suite via ``tests/conftest.py``).

The application-factory pattern
-------------------------------
Rather than create a module-level ``app`` object, the application is built by a
function. This is the idiomatic Flask structure mandated by the AAP
(Sections 0.1.2 and 0.7) and yields three concrete benefits:

* **Multiple instances / configurations.** ``create_app("testing")`` and
  ``create_app("production")`` each return an independently configured app, so
  the test-suite can spin up an isolated instance without disturbing the
  production wiring.
* **Deferred, ordered wiring.** Extensions are declared *unbound* in
  :mod:`app.extensions` and bound to the concrete app *inside* the factory via
  ``init_app(app)``; blueprints, request hooks, and error handlers are attached
  in a deterministic order that mirrors the original Express pipeline.
* **Stable import surface.** Sibling modules import the factory's collaborators
  (``get_config``, ``cors``, ``register_blueprints``, ``register_hooks``,
  ``register_error_handlers``) through ``register_*`` indirection, which keeps
  this file unchanged as resources are ported and avoids circular imports.

Hard contracts (other already-created files depend on these -- DO NOT deviate)
------------------------------------------------------------------------------
1. The repo-root ``wsgi.py`` entrypoint performs ``from app import create_app``
   then ``app = create_app()``. Therefore :func:`create_app` is defined at
   module level, is named EXACTLY ``create_app``, and is callable with ZERO
   arguments (``config_name`` defaults to ``None``).
2. ``tests/conftest.py`` selects the testing profile via
   ``create_app("testing")``. Therefore :func:`create_app` accepts an optional
   config-name argument that is forwarded to :func:`app.config.get_config`.
3. The returned object is a :class:`flask.Flask` instance, so
   ``gunicorn wsgi:app`` (and the factory form ``gunicorn 'app:create_app()'``)
   can serve it directly.

Scope & parity mandate (AAP Sections 0.1, 0.6.2, and 0.7)
---------------------------------------------------------
This is a behavioral-parity port of an original Node.js server that is **not
yet present** in the repository (AAP Section 0.1, "Critical Precondition"): the
only tracked source is ``README.md`` (``# Artifact2``). Because a faithful port
is defined entirely by the source it mirrors, this factory ships ONLY the
source-agnostic foundation that makes the application "empty-but-bootable"
(AAP Section 0.5.2). It defines NO routes, views, models, database access, or
business rules -- fabricating any of those would violate the parity mandate
(*nothing invented, nothing dropped*, AAP Sections 0.6.2 and 0.7). Each ported
resource is wired in later through the existing ``register_*`` collaborators,
one-to-one with the original source, without editing this file.

Configuration & ``.env`` loading
---------------------------------
This module does NOT read the process environment for configuration and does
NOT call ``load_dotenv()``. That responsibility belongs entirely to
:mod:`app.config`, which calls ``load_dotenv()`` as its first executable
statement (before its ``Config`` classes are evaluated). Because this module
imports :mod:`app.config` at module top, the ``.env`` file is loaded before
:func:`create_app` is ever called. Configuration flows exclusively through
:func:`app.config.get_config`; no secrets are hardcoded here (AAP Section 0.7).
"""

import os

from flask import Flask

# Absolute imports only (AAP Sections 0.3.2 and 0.7); never relative. Each of
# the five internal collaborators below is a fixed contract implemented by an
# already-created sibling module. None of them imports ``app`` at module scope,
# so these module-top imports cannot form a circular import with this factory.
from app.config import get_config
from app.extensions import cors
from app.blueprints import register_blueprints
from app.middleware.hooks import register_hooks
from app.middleware.error_handlers import register_error_handlers


def create_app(config_name: str | None = None) -> Flask:
    """Construct, configure, and return a Flask application instance.

    This is the application's composition root. It performs only declarative
    wiring -- it contains no route, view, model, or database logic -- assembling
    the foundation in the exact pipeline order documented in AAP Section 0.4.2
    (the order is revisited only to match the original middleware order once the
    Node.js source is supplied):

    1. **Instantiate** the core :class:`flask.Flask` application.
    2. **Load configuration** by resolving the active ``Config`` class through
       :func:`app.config.get_config` and applying it via
       :meth:`flask.Config.from_object`, then invoking the config class's
       ``init_app`` extension hook.
    3. **Initialize extensions** -- bind the (currently single) shared extension
       singleton, :data:`app.extensions.cors`, to the app via ``init_app``.
    4. **Register blueprints** through :func:`app.blueprints.register_blueprints`
       (a no-op in the foundation; it grows one entry per ported Express router).
    5. **Attach the request pipeline** -- request lifecycle hooks via
       :func:`app.middleware.hooks.register_hooks`, then centralized error
       handlers via :func:`app.middleware.error_handlers.register_error_handlers`.

    Args:
        config_name: Optional configuration profile selector -- one of
            ``"development"``, ``"production"``, ``"testing"``, or ``"default"``.
            When ``None`` (the common call from ``wsgi.py`` / gunicorn),
            :func:`app.config.get_config` falls back to the ``APP_CONFIG``
            environment variable, ultimately defaulting to the development
            profile. ``tests/conftest.py`` passes ``"testing"`` explicitly.

    Returns:
        flask.Flask: A fully configured Flask application, ready to be served by
        a WSGI server or driven by the test client.
    """
    # (1) Instantiate the core Flask application. ``__name__`` anchors Flask's
    # root path so it can locate the package's ``instance``, ``static``, and
    # ``templates`` folders relative to this module.
    app = Flask(__name__)

    # (2) Load configuration.
    #
    # Resolve the active configuration CLASS exactly once and reuse it for both
    # the ``from_object`` load and the ``init_app`` hook (calling ``get_config``
    # twice would re-resolve the same class needlessly). ``get_config`` owns all
    # environment-variable resolution -- including the ``APP_CONFIG`` fallback
    # when ``config_name`` is ``None`` -- so no env var is re-read here.
    selected_config = get_config(config_name)

    # ``from_object`` copies only the class's UPPER_CASE attributes (SECRET_KEY,
    # HOST, PORT, DEBUG, TESTING, ...) into ``app.config``.
    app.config.from_object(selected_config)

    # Invoke the configuration's per-environment initialization hook. The base
    # ``Config.init_app`` is a no-op, so this call is always safe regardless of
    # the active profile; subclasses (or future source-derived configuration)
    # may override it to add environment-specific setup.
    selected_config.init_app(app)

    # Ensure Flask's instance folder exists. This is standard, idiomatic Flask
    # factory plumbing (the application's writable, deploy-local directory for
    # instance configuration and runtime files); it is infrastructure only and
    # introduces NO route, model, or externally observable behavior. ``exist_ok``
    # makes the call an idempotent no-op when the folder is already present.
    os.makedirs(app.instance_path, exist_ok=True)

    # (3) Initialize extensions.
    #
    # Bind the shared, unbound CORS singleton to this app, reproducing the
    # original Express server's ``cors`` middleware. CORS is the ONLY extension
    # in the source-agnostic foundation (it is the only bindable Flask extension
    # in the active ``requirements.txt`` tier). Additional extensions (database,
    # JWT, rate limiter, ...) are bound here later via ``<ext>.init_app(app)``
    # once they are added to ``app/extensions.py`` and their pins are activated
    # in ``requirements.txt`` -- one-to-one with the original source.
    cors.init_app(app)

    # (4) Register blueprints.
    #
    # Mount every ported Express router at its original URL prefix. In the
    # foundation this registry is empty, so the call is a safe no-op; it grows
    # one entry per ported router without any change to this factory.
    register_blueprints(app)

    # (5) Attach the request/response pipeline, in the original middleware order.
    #
    # Request lifecycle hooks first (``before_request`` / ``after_request``,
    # mirroring the Express global middleware stack)...
    register_hooks(app)
    # ...then the centralized JSON error handlers as the final pipeline step
    # (mirroring the Express ``(err, req, res, next)`` error-handling middleware).
    register_error_handlers(app)

    # Return the fully assembled application to the caller (``wsgi.py`` /
    # gunicorn, or the pytest fixtures).
    return app
