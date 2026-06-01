"""Production WSGI entrypoint for the Artifact2 Flask application.

This module is the single composition entrypoint that exposes the WSGI
application object a production server targets. It maps the original Node.js
(Express) bootstrap (``app.js`` / ``server.js`` / ``index.js`` and its
``app.listen(...)`` call) onto the Python/Flask world (AAP Sections 0.4.2 and
0.4.3): where the Node entrypoint constructed the server and began listening,
this module asks the :func:`app.create_app` application factory to build a
fully configured :class:`flask.Flask` instance and binds it to the
module-level name ``app``.

Production usage (gunicorn)
---------------------------
The application object is exposed as ``app`` so the standard WSGI server target
``wsgi:app`` resolves directly::

    gunicorn wsgi:app
    gunicorn --bind 0.0.0.0:3000 --workers 4 wsgi:app

gunicorn imports this module, reads the module-level ``app`` object, and serves
it. It NEVER executes the ``if __name__ == "__main__":`` block below -- that
block is only reached when the file is run directly (``python wsgi.py``) for
local development convenience.

Scope & parity mandate (AAP Sections 0.5.2, 0.6.2, and 0.7)
-----------------------------------------------------------
This is the source-agnostic foundation that makes the application
"empty-but-bootable" before any route is ported. It is an entrypoint ONLY: it
contains no routes, views, models, database access, or business logic --
fabricating any of those would violate the behavioral-parity mandate (*nothing
invented, nothing dropped*). All application wiring lives in the factory
(``app/__init__.py``); this file merely instantiates it.

Configuration
-------------
This module does NOT read configuration for the application itself and does NOT
call ``load_dotenv()``. The factory (via :mod:`app.config`) owns configuration
loading -- including reading any local ``.env`` file -- so by the time
:func:`create_app` returns, the environment has already been loaded. The
``HOST`` / ``PORT`` reads in the development runner below therefore observe the
same values the application was configured with. No secrets are hardcoded here.
"""

import os

# Import the application factory from the ``app`` package's ``__init__.py``.
# This is a fixed contract: the factory is named EXACTLY ``create_app`` and is
# callable with zero arguments (its ``config_name`` argument defaults to
# ``None``, which makes the factory resolve the active profile from the
# ``APP_CONFIG`` environment variable). Any import or boot error raised by the
# factory is deliberately allowed to surface (it is NOT caught here) so that a
# misconfigured application fails loudly at startup instead of serving a
# half-initialized instance.
from app import create_app

# The module-level WSGI application object. Naming it EXACTLY ``app`` is what
# lets ``gunicorn wsgi:app`` (and ``flask --app wsgi run``) locate it. Binding
# the factory's return value to the name ``app`` does not shadow the imported
# ``app`` package: the ``from app import create_app`` statement above only bound
# the name ``create_app`` into this module's namespace, never the package
# itself. This object exposes the standard Flask surface used by callers --
# notably ``app.run(...)`` (development server, below) and ``app.config`` (the
# configuration the factory loaded).
app = create_app()


if __name__ == "__main__":
    # ---- Local development convenience runner -- NOT for production. ----
    #
    # Reached only via ``python wsgi.py``. In production the application is
    # served by gunicorn (``gunicorn wsgi:app``), which imports the ``app``
    # object above and never executes this block. Flask's built-in server
    # started by ``app.run`` is single-process and intended for development
    # only; it must not be used to serve production traffic.
    #
    # HOST / PORT are read from the environment with safe defaults that mirror
    # ``app/config.py`` and ``.env.example`` (HOST=0.0.0.0, PORT=3000 -- the
    # latter mirroring the original Express server's ``process.env.PORT``
    # default). The factory has already loaded any local ``.env`` (through
    # ``app.config``), so these reads agree with the running configuration.
    host = os.environ.get("HOST", "0.0.0.0")
    try:
        # ``PORT`` is always a string in the environment; coerce it to int.
        port = int(os.environ.get("PORT", "3000"))
    except ValueError:
        # Tolerate a malformed ``PORT`` (e.g. ``PORT=not_an_int``) by falling
        # back to the documented default instead of crashing the dev runner --
        # the same safe-default behavior ``app/config.py`` applies at import.
        port = 3000

    # ``debug`` is intentionally NOT passed here: the active configuration
    # profile (loaded by the factory into ``app.config["DEBUG"]``) already
    # governs Flask's debug/reloader behavior, keeping a single authoritative
    # source for that switch.
    app.run(host=host, port=port)
