"""Flask Blueprint registry for the Artifact2 application.

This package groups the Flask blueprint objects that mirror the original
Node.js (Express) server's routers **one-to-one**. It is the *route layer's
composition point*: it exposes a single function, :func:`register_blueprints`,
that the application factory (``app/__init__.py``) calls to mount every
blueprint at its original URL prefix, reproducing the route tree exactly.

Role in the application
-----------------------
Where the original Express server registered routers with
``app.use("/users", usersRouter)`` (and similar), the Flask port registers
blueprints with ``app.register_blueprint(users_bp, url_prefix="/users")``. Each
Express ``express.Router()`` module maps to exactly one
``app/blueprints/<resource>/routes.py`` blueprint, and each such blueprint is
wired here so the factory has a single, stable entry point for the whole route
layer (AAP Sections 0.4.2, 0.4.3, and 0.5.1, Group 2).

Hard contract with the application factory (match EXACTLY)
----------------------------------------------------------
``app/__init__.py`` performs, at module top, the absolute import::

    from app.blueprints import register_blueprints

and then, inside ``create_app(...)`` as factory step (4) -- AFTER
``cors.init_app(app)`` and BEFORE ``register_hooks(app)`` /
``register_error_handlers(app)`` -- it calls::

    register_blueprints(app)

The exported symbol therefore MUST be named exactly ``register_blueprints``,
MUST accept the Flask ``app`` as its single positional argument, and returns
``None`` (consistent with the sibling ``register_hooks(app)`` /
``register_error_handlers(app)`` pattern). This ``register_*`` indirection keeps
the factory stable and avoids circular imports as resources are added.

Scope & parity mandate (AAP Sections 0.1, 0.6.2, and 0.7)
---------------------------------------------------------
This is a behavioral-parity port of an original Node.js server that is **not
yet present** in the repository (AAP Section 0.1, "Critical Precondition"): the
only tracked source is ``README.md`` (``# Artifact2``). Because a faithful port
is defined entirely by the source it mirrors, there are **no Express routers to
reproduce yet**. Accordingly this package ships ONLY the source-agnostic
foundation: a :func:`register_blueprints` that is a **no-op ready to grow**. No
resource blueprint is created, imported, or registered here -- fabricating any
endpoint would violate the parity mandate (*nothing invented, nothing
dropped*). Each ``<resource>`` blueprint is added one-to-one only once the
original source supplies the matching Express router.

Import-safety guarantee
-----------------------
This module imports nothing at module scope (the foundation form has no imports
at all) and constructs no Flask instance, no blueprint object, and no view
function. As a result, ``import app.blueprints`` -- and therefore the factory's
top-level ``from app.blueprints import register_blueprints`` -- can never fail
on a not-yet-written resource module or a not-yet-installed conditional
dependency. Future resource blueprints are imported **lazily inside**
:func:`register_blueprints` (never at module top) so this guarantee survives as
the route layer grows; see the registration protocol inside the function body.
"""


def register_blueprints(app):
    """Mount every application blueprint onto *app*.

    Called by the application factory (``app/__init__.py``) as step (4) of
    ``create_app(...)`` -- after the extensions are bound (``cors.init_app(app)``)
    and before the request lifecycle hooks and error handlers are attached
    (``register_hooks(app)`` / ``register_error_handlers(app)``). This ordering
    reproduces the original Express middleware/route pipeline order.

    The function builds a list of ``(blueprint, url_prefix)`` pairs and registers
    each pair on *app* via :meth:`flask.Flask.register_blueprint`. In the current
    foundation form that list is intentionally **empty**, so the call is a safe
    no-op: it registers zero blueprints and returns ``None``. The empty-list plus
    registration-loop shape means the route layer is "ready to grow" -- adding a
    ported resource later is a two-line change (a lazy local import plus an
    ``.append(...)``) with the loop left untouched.

    Growth protocol (parity-gated -- do NOT activate until the source exists):
        For each Express router in the supplied Node.js source, create the
        matching ``app/blueprints/<resource>/routes.py`` blueprint, then wire it
        here by importing it **lazily inside this function** and appending it
        with the SAME ``url_prefix`` the original router used. Lazy/local imports
        (rather than module-top imports) are deliberate: resource blueprint
        modules import services that import ``app.extensions``, so importing them
        at module scope could create an import cycle with the factory. Performing
        the import inside this function defers it until ``create_app`` runs, after
        the package graph is fully importable.

    Example::

        # Uncomment ONLY when app/blueprints/users/routes.py exists in the
        # supplied source (illustrative -- NOT active code):
        #
        #     from app.blueprints.users.routes import users_bp
        #     blueprints.append((users_bp, "/users"))

    Args:
        app: The Flask application instance created by ``create_app(...)``.
            Must expose :meth:`flask.Flask.register_blueprint`.

    Returns:
        None. Registration is performed for its side effect on *app*, mirroring
        the sibling ``register_hooks(app)`` / ``register_error_handlers(app)``
        functions.
    """
    # List of (blueprint, url_prefix) pairs to mount. Intentionally EMPTY: the
    # original Node.js source is absent, so there are no Express routers to
    # mirror yet (AAP Section 0.1, "Critical Precondition"). Each ported router
    # adds exactly one entry here, one-to-one with the source.
    blueprints = []  # (blueprint, url_prefix) -- empty until the source is supplied

    # -----------------------------------------------------------------------
    # BLUEPRINT-REGISTRATION PROTOCOL  (documentation only -- NOT executed)
    # -----------------------------------------------------------------------
    # When the original source IS supplied, wire each Express router here in
    # three steps, preserving the original URL prefix exactly:
    #
    #   1. Create app/blueprints/<resource>/routes.py defining the resource
    #      blueprint object (a module-level instance, e.g. ``users_bp``).
    #   2. Import that blueprint LAZILY, inside this function (never at module
    #      top), using an absolute import.
    #   3. Append a (blueprint, url_prefix) pair to ``blueprints`` above.
    #
    # The import MUST stay inside this function: resource blueprint modules
    # import services that import ``app.extensions``, so a module-top import
    # could form a circular import with the factory. Keeping it local defers
    # the import until create_app() runs, after the package graph is complete.
    #
    # Illustrative example (COMMENTED -- do NOT uncomment until the matching
    # Express router exists in the supplied source):
    #
    #     from app.blueprints.users.routes import users_bp
    #     blueprints.append((users_bp, "/users"))
    #
    #     from app.blueprints.auth.routes import auth_bp
    #     blueprints.append((auth_bp, "/auth"))
    # -----------------------------------------------------------------------

    # Register every collected blueprint on the application. With an empty list
    # this loop is a safe no-op now and needs ZERO changes as resources are
    # added -- each new entry appended above is picked up automatically.
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)


# Public API of this module: only the factory-facing registrar is exported.
# Mirrors the sibling modules' convention (``app/extensions.py`` exports
# ``cors``; ``app/config.py`` exports its config classes and ``get_config``).
__all__ = ["register_blueprints"]
