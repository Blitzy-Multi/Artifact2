"""Shared pytest fixtures for the Artifact2 Flask test suite.

This is the ``conftest.py`` for the entire ``tests/`` tree. pytest auto-discovers
it and makes the fixtures it defines available -- without any import -- to every
current and future test module collected under ``tests/`` (collection is confined
to that tree by ``testpaths = ["tests"]`` in the repo-root ``pyproject.toml``).

Role in the project (AAP Sections 0.5.1 Group 3, 0.6.1, and 0.6.3)
------------------------------------------------------------------
The Artifact2 project is a behavioral-parity port of an existing Node.js
(Express) server to Python 3 + Flask. The pytest suite is the *acceptance gate*
for that parity (AAP Section 0.6.3): it replaces the original
``jest`` / ``mocha`` / ``supertest`` tests and, once the original source is
supplied, asserts that identical inputs produce identical outputs (same routes,
status codes, response bodies/headers, and error envelopes). This module is the
shared foundation those parity tests build upon.

Source-agnostic foundation only (AAP Sections 0.1, 0.6.2, and 0.7)
------------------------------------------------------------------
The original Node.js source is **not yet present** in the repository (AAP
Section 0.1, "Critical Precondition"). A faithful port is defined entirely by
the source it mirrors, so this file deliberately ships ONLY the source-agnostic
test scaffold -- the ``app``, ``client``, and ``runner`` fixtures. It defines NO
resource-specific fixtures, seeded records, factory helpers, auth tokens, or
route/model assertions: fabricating any of those would violate the parity
mandate (*nothing is invented and nothing is dropped*). Those are authored
one-to-one against the supplied source later, under ``tests/unit/`` and
``tests/integration/``. See the "Deferred fixtures" note at the bottom of this
module for the database/session and per-resource fixtures that are intentionally
withheld until the source selects them.

Application-factory isolation
-----------------------------
Every fixture builds its application through the factory :func:`app.create_app`
-- never a module-level/global :class:`flask.Flask` instance -- and the fixtures
are function-scoped (pytest's default). Together these guarantee that each test
receives a fresh, fully isolated application configured for testing, so state can
never leak between tests. ``create_app("testing")`` selects ``TestingConfig``
(which sets ``TESTING=True``); see ``app/config.py``.

Configuration ownership
-----------------------
This module performs no configuration and loads no environment variables.
``.env`` loading and all configuration values are owned by ``app/config.py``
(it calls ``load_dotenv()`` at import time), and pytest configuration
(``testpaths``, discovery patterns, markers, ``addopts``) lives exclusively in
the repo-root ``pyproject.toml`` ``[tool.pytest.ini_options]`` table -- neither
is duplicated here.
"""

# Absolute imports only (AAP Sections 0.3.2 and 0.7); never relative. Only the
# two collaborators below are required by this scaffold: ``pytest`` for the
# fixture decorator/runner, and the application factory ``create_app``. No
# resource-specific, database, or model imports appear here because none exist
# yet -- importing a not-yet-installed conditional dependency would crash test
# collection (AAP Section 0.3.1).
import pytest

from app import create_app


@pytest.fixture
def app():
    """Create a fresh Flask application configured for testing.

    The application is built through the factory (never a global app) so each
    test receives an isolated instance, and the fixture keeps pytest's default
    function scope so no application state leaks between tests.
    ``create_app("testing")`` activates ``TestingConfig``, which sets
    ``TESTING=True`` (and ``DEBUG=True``) -- under which Flask propagates
    exceptions to the caller instead of returning an opaque ``500``, giving
    clearer test failures.

    ``app.config.update(TESTING=True)`` is a defensive guarantee that mirrors
    the canonical Flask testing scaffold: ``TestingConfig`` already enables
    testing mode, and this restates it so the fixture's contract holds even if
    the resolved profile were to change. It does not re-implement configuration
    (that responsibility remains owned by ``app/config.py``).

    The application is yielded (not returned) so that teardown logic -- for
    example a database rollback once a data layer is introduced -- can be added
    after the ``yield`` later WITHOUT changing this fixture's signature or any
    dependent fixture/test. No application or request context is pushed here:
    the Flask test client (see :func:`client`) manages request/application
    contexts per request, which is sufficient for the current foundation. (A
    ``with app.app_context(): yield app`` form may be adopted LATER, only if a
    future database/extension fixture comes to require an ambient application
    context -- noted here as a forward-looking comment, not implemented now.)

    Yields:
        flask.Flask: A fully configured application instance in testing mode.
    """
    app = create_app("testing")
    app.config.update(TESTING=True)  # defensive: guarantee testing mode
    yield app


@pytest.fixture
def client(app):
    """Provide a Werkzeug test client bound to the testing application.

    Derived from the :func:`app` fixture, so it inherits the same isolated,
    testing-configured application. Integration/contract tests use this client
    to issue HTTP requests and assert behavioral parity with the original
    server -- identical method + path, status codes, response bodies/headers,
    and error envelopes -- once routes are ported from the supplied source.

    Args:
        app (flask.Flask): The testing application provided by the :func:`app`
            fixture.

    Returns:
        flask.testing.FlaskClient: A test client for issuing requests to the
        application in-process, without running a live server.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """Provide a Click CLI runner bound to the testing application.

    Derived from the :func:`app` fixture so CLI commands execute against the
    same isolated, testing-configured application. This is the canonical,
    source-agnostic Flask CLI-test fixture; it assumes no routes or models and
    is used to invoke any Flask/Click commands registered on the app (for
    example custom ``flask`` subcommands ported from the original tooling) and
    to assert on their output and exit codes.

    Args:
        app (flask.Flask): The testing application provided by the :func:`app`
            fixture.

    Returns:
        flask.testing.FlaskCliRunner: A runner for invoking registered CLI
        commands within the application's context.
    """
    return app.test_cli_runner()


# ===========================================================================
# DEFERRED FIXTURES  (documentation only -- intentionally NOT implemented)
# ===========================================================================
#
# The fixtures below are deliberately WITHHELD until the original Node.js source
# is supplied, because a behavioral-parity port invents nothing ahead of its
# source (AAP Sections 0.6.2 and 0.7). They are described here purely so the
# intended extension points are unambiguous; this block contains NO executable
# code and imports NO not-yet-installed package (doing either would break test
# collection -- AAP Section 0.3.1).
#
# --- Database / session fixture --------------------------------------------
#   A "db" (or "session") fixture that creates the schema, begins a nested
#   transaction per test, and rolls it back on teardown will be added ONLY when
#   a database extension is selected from the source -- the SQL ORM (via
#   Flask-SQLAlchemy) or the MongoDB driver (via Flask-PyMongo) -- that is, only
#   after (1) the matching pin is uncommented in "requirements.txt" and
#   installed, and (2) the corresponding singleton is declared in
#   "app/extensions.py" and bound in the factory. The active dependency tier
#   currently installs NO database driver and "app/extensions.py" defines only
#   "cors", so no such fixture exists yet. When introduced, the "app" fixture
#   above will likely push an application context
#   ("with app.app_context(): yield app") so the data layer has an ambient
#   context during per-test setup and teardown.
#
# --- Per-resource fixtures --------------------------------------------------
#   Resource-specific fixtures -- authentication tokens, seeded entities, model
#   factories, and request-payload builders -- are authored ONE-TO-ONE against
#   the supplied source, under "tests/unit/" (service/model coverage) and
#   "tests/integration/" (endpoint/contract coverage). None are defined here
#   because no endpoints, models, or business rules exist in the repository yet.
# ===========================================================================
