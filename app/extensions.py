"""Shared Flask extension singletons for the Artifact2 application.

This module implements the canonical Flask *extension-object* pattern: each
extension is instantiated **once, unbound** (i.e. without an application
instance) at import time, and is later bound to the concrete app inside the
application factory (``app/__init__.py``) via ``<ext>.init_app(app)``.

Why the extension-object pattern?
---------------------------------
Declaring the singletons here -- rather than inside ``create_app()`` -- gives
the rest of the codebase a single, stable import location for every shared
extension (e.g. ``from app.extensions import cors``). It also keeps the
application factory free of construction details and allows several app
instances (development, testing, production, CLI) to each bind the very same
singleton objects through ``init_app``. This is the structure recommended by
the Flask documentation and mandated by the Agent Action Plan (AAP
Sections 0.4.2 and 0.5.1, Group 1).

Hard contract with the application factory
------------------------------------------
``app/__init__.py`` performs::

    from app.extensions import cors
    # ... remaining factory setup ...
    cors.init_app(app)

The exported symbol therefore MUST be named exactly ``cors``.

Scope & minimalism mandate (AAP Section 0.3.1)
----------------------------------------------
This project is a behavioral-parity port of an original Node.js (Express)
server that is **not yet present** in the repository (AAP Section 0.1,
"Critical Precondition"). Because the concrete dependency subset can only be
finalized one-to-one against that source, the *active* dependency tier in
``requirements.txt`` currently contains exactly ONE bindable Flask extension
library -- ``Flask-Cors==6.0.2``. Accordingly, this module defines exactly ONE
singleton: ``cors`` (replacing the original server's ``cors`` middleware).

Import-safety guarantee
-----------------------
This module imports ONLY libraries present in the active ``requirements.txt``
tier. It performs no configuration reads, constructs no ``Flask`` application
instance, and contains no business logic. As a consequence,
``import app.extensions`` (and therefore ``import app``) can never fail on a
not-yet-installed conditional dependency. See the commented "extension-add
protocol" at the bottom of this file for the procedure to add further
extensions one-to-one with the original source once it is supplied.
"""

from flask_cors import CORS

# ---------------------------------------------------------------------------
# Unbound extension singletons
#
# Each object below is created WITHOUT an ``app`` argument. The application
# factory (``app/__init__.py``) binds it to the live application with
# ``<ext>.init_app(app)``, at which point the extension reads the app's
# configuration and registers its request hooks / response handlers.
# ---------------------------------------------------------------------------

# Cross-Origin Resource Sharing (CORS) -- the Python replacement for the
# original Express server's ``cors`` middleware (AAP Section 0.3.2). It is
# instantiated unbound here and bound by the factory via ``cors.init_app(app)``
# (optionally passing resource/origin options sourced from configuration) so
# that the original cross-origin policy is reproduced exactly.
cors = CORS()

# Public API of this module. Only the (later-bound) extension singletons are
# exported; the imported ``CORS`` class is an implementation detail and is not
# part of the public surface.
__all__ = ["cors"]


# ===========================================================================
# EXTENSION-ADD PROTOCOL  (documentation only -- intentionally NOT executed)
# ===========================================================================
#
# When the original Node.js source IS supplied, extend this module one-to-one
# with the original's stack. For EACH concern the original ``package.json``
# declares, follow these three steps:
#
#   1. Uncomment the matching, version-pinned line in ``requirements.txt`` and
#      run ``pip install -r requirements.txt`` so the library is installed.
#   2. Add the corresponding UNBOUND singleton in THIS file (mirroring the
#      ``cors = CORS()`` style above) using an absolute import.
#   3. Bind it inside the factory in ``app/__init__.py`` via
#      ``<ext>.init_app(app)``, in the same pipeline order the original
#      middleware used.
#
# The snippets below are COMMENTED EXAMPLES ONLY. Do NOT uncomment any of them
# until its backing library is uncommented in ``requirements.txt`` and
# installed; importing a not-yet-installed package here would break
# ``import app`` and the application's bootability (AAP Section 0.3.1).
#
# --- SQL data layer (original used sequelize / knex / pg / mysql2) ----------
#       from flask_sqlalchemy import SQLAlchemy
#       db = SQLAlchemy()                 # factory: db.init_app(app)
#
# --- MongoDB data layer (original used mongoose / mongodb) ------------------
#       from flask_pymongo import PyMongo
#       mongo = PyMongo()                 # factory: mongo.init_app(app)
#
# --- Authentication / JWT (original used jsonwebtoken) ----------------------
#       # PyJWT (the ``jwt`` package) is a stateless helper with no init_app;
#       # import and use it directly inside services. If an extension-style
#       # manager is adopted instead, declare it here, e.g.:
#       #       from flask_jwt_extended import JWTManager
#       #       jwt = JWTManager()        # factory: jwt.init_app(app)
#
# --- Rate limiting / throttling (original used express-rate-limit) ----------
#       from flask_limiter import Limiter
#       from flask_limiter.util import get_remote_address
#       limiter = Limiter(key_func=get_remote_address)
#                                         # factory: limiter.init_app(app)
#
# --- Realtime / websockets (original used socket.io) ------------------------
#       from flask_socketio import SocketIO
#       socketio = SocketIO()             # factory: socketio.init_app(app)
#
# ===========================================================================
