"""Environment-driven application configuration for the Artifact2 Flask app.

This module centralises every runtime configuration value the application
consumes into a small ``Config`` class hierarchy. The active configuration is
selected at startup by an environment variable (``APP_CONFIG``) and resolved
through :func:`get_config`, which the application factory
(``app/__init__.py``) passes to ``app.config.from_object(...)``.

Design (idiomatic Flask)
------------------------
* A base :class:`Config` defines the universal defaults.
* Per-environment subclasses (:class:`DevelopmentConfig`,
  :class:`ProductionConfig`, :class:`TestingConfig`) override only what differs
  between environments.
* :data:`CONFIG_MAP` maps the public selector names (plus a ``"default"``
  alias) to those classes, and :func:`get_config` performs the lookup.

This mirrors the original Node.js server's ``process.env.*`` configuration
surface (AAP Sections 0.4.2, 0.4.3, 0.5.1 Group 1, and 0.7); the AAP is the
primary authority for this file.

dotenv load ordering (IMPORTANT)
--------------------------------
:func:`dotenv.load_dotenv` is invoked as the FIRST executable statement in this
module -- before the module-level configuration helpers or any ``Config`` class
are defined. The ``Config`` attributes call ``os.environ.get(...)`` (directly or
through the ``_get_int_env`` / ``_get_bool_env`` helpers) while the class body
executes (i.e. at import time), so the ``.env`` file MUST already be loaded into
``os.environ`` by then. The helpers themselves read ``os.environ`` only when
CALLED (from inside the class bodies), which is always after ``load_dotenv()``
has run, so defining them after the load call is safe. Loading ``.env`` later
(for example inside the factory) would be too late: the class attributes would
have already been bound to the process defaults. ``load_dotenv()`` is a safe
no-op when no ``.env`` file is present (only the committed ``.env.example``
template ships with the repository; ``.env`` itself is git-ignored), in which
case the documented defaults below apply.

Hard contracts (coordination with already-created files -- match EXACTLY)
-------------------------------------------------------------------------
1. Repo-root ``.env.example`` defines the ACTIVE variables this module reads, by
   the SAME key names: ``FLASK_APP``, ``FLASK_DEBUG``, ``APP_CONFIG`` (the
   selector), ``SECRET_KEY``, ``HOST``, and ``PORT``. EVERY active key in that
   template is consumed here under its identical name, so the env template and
   this module stay in lock-step (CP1 active-key parity). ``FLASK_APP`` and
   ``FLASK_DEBUG`` are *additionally* honoured by the Flask CLI (``flask run`` /
   ``flask shell``); mirroring them onto the ``Config`` surface keeps a single,
   authoritative configuration source instead of a split CLI-only set. The
   defaults below match the ``.env.example`` placeholders exactly:
   ``FLASK_APP=wsgi.py``, ``FLASK_DEBUG=0`` (off), ``APP_CONFIG=development``,
   ``SECRET_KEY`` placeholder, ``HOST=0.0.0.0``, and ``PORT=3000``.
2. ``app/__init__.py`` calls ``get_config(config_name)`` and feeds the result to
   ``app.config.from_object(...)``; this module therefore exposes
   :func:`get_config` alongside the config classes.
3. ``tests/conftest.py`` selects the testing profile via
   ``create_app("testing")`` -> ``get_config("testing")``; hence
   :class:`TestingConfig` exists and ``APP_CONFIG=testing`` resolves to it.

Scope & parity mandate (AAP Sections 0.6.2 and 0.7)
---------------------------------------------------
This is a behavioral-parity port of an original Node.js server that is NOT yet
present in the repository (AAP Section 0.1, "Critical Precondition"). Only the
universal, source-agnostic configuration surface is defined here. Source-derived
variables (database URI, JWT secret, CORS origins, rate limits, log level, ...)
live as COMMENTED, inert entries in ``.env.example`` and are added to this module
ONE-TO-ONE only once the original source selects them. Nothing is invented and
nothing is dropped.
"""

import os

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from a local ``.env`` file (if present) BEFORE any
# Config class body executes. This MUST be the first executable statement in the
# module: the class attributes below read ``os.environ`` at class-definition
# (import) time, so the ``.env`` values have to be present in the environment
# already. When no ``.env`` exists the call is a harmless no-op and the documented
# defaults apply.
# ---------------------------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------------------------
# Small, robust environment-coercion helpers.
#
# Environment variables are ALWAYS strings, so values that the application wants
# as an ``int`` or ``bool`` have to be coerced. A naive ``int(os.environ[...])``
# raises and crashes the whole module at import time when the operator supplies a
# malformed value (for example ``PORT=not_an_int``). These helpers coerce safely,
# falling back to a documented default instead of aborting application start-up.
# They read ``os.environ`` only when CALLED (from the class bodies below), which
# is always after ``load_dotenv()`` has populated the environment.
# ---------------------------------------------------------------------------
def _get_int_env(name, default):
    """Read an integer-valued environment variable with a safe fallback.

    Coerces ``os.environ[name]`` to ``int``. When the variable is absent, empty,
    or not a valid base-10 integer (e.g. ``PORT=not_an_int``), the provided
    ``default`` is returned instead of raising ``ValueError`` -- which would
    otherwise crash configuration loading at import time and prevent the app from
    starting at all. This implements the CP1 "safe default" requirement for
    ``PORT`` parsing.

    Args:
        name: The environment variable name to read.
        default (int): Value returned when the variable is missing or malformed.

    Returns:
        int: The parsed integer, or ``default`` on any missing/invalid input.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        # A malformed value must never crash configuration loading; fall back to
        # the documented safe default so the application can still start.
        return default


def _get_bool_env(name, default):
    """Read a boolean-valued environment variable using common truthy tokens.

    Interprets values the same way the Flask CLI interprets ``FLASK_DEBUG``: the
    tokens ``"1"``, ``"true"``, ``"yes"``, and ``"on"`` (case-insensitive,
    surrounding whitespace ignored) are ``True``; ``"0"``, ``"false"``, ``"no"``,
    ``"off"``, and the empty string are ``False``. When the variable is ABSENT
    the supplied ``default`` is returned -- this lets each environment profile
    pick its own sensible default while still allowing an explicit environment
    value to override it.

    Args:
        name: The environment variable name to read.
        default (bool): Value returned when the variable is not set at all.

    Returns:
        bool: ``True``/``False`` parsed from the value, or ``default`` when unset.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration: the universal defaults shared by every environment.

    Subclasses override only the attributes that differ for their environment.
    Flask's ``from_object`` loads only UPPER_CASE attribute names into
    ``app.config``, so only the upper-cased names below form the public
    configuration surface; helper methods such as :meth:`init_app` are not
    loaded as config values.
    """

    # Flask CLI application entrypoint, mirrored from the ``FLASK_APP`` env var
    # (default ``wsgi.py``). The ``flask`` command reads ``FLASK_APP`` straight
    # from the environment; exposing it here as well keeps a single authoritative
    # configuration surface and satisfies the env<->config active-key parity
    # contract (every active ``.env.example`` key is read here under the same
    # name). Flask does not consume ``app.config["FLASK_APP"]`` at runtime, so
    # this attribute is documentation/parity only and has no runtime side effect.
    FLASK_APP = os.environ.get("FLASK_APP", "wsgi.py")

    # Secret used by Flask / ItsDangerous to sign session cookies and other
    # signed tokens. The default is an OBVIOUS, non-secret placeholder that
    # matches ``.env.example``; it exists purely for local-development
    # convenience. Production MUST override it with a strong random value
    # supplied via the ``SECRET_KEY`` environment variable (see
    # :class:`ProductionConfig`). A real secret is NEVER committed here.
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-your-local-env")

    # Network interface the server binds to. ``0.0.0.0`` listens on all
    # interfaces (container-friendly); use ``127.0.0.1`` to restrict to
    # localhost. Matches ``.env.example`` (HOST=0.0.0.0).
    HOST = os.environ.get("HOST", "0.0.0.0")

    # TCP port the server listens on. Parsed through ``_get_int_env`` so a
    # MISSING *or* MALFORMED value (e.g. ``PORT=not_an_int``) safely falls back
    # to the default instead of raising ``ValueError`` at import time and
    # crashing the application before it can start. The default ``3000`` mirrors
    # the original Express server's ``process.env.PORT`` default and matches both
    # ``.env.example`` (PORT=3000) and the README run examples
    # (``gunicorn --bind 0.0.0.0:3000 wsgi:app``).
    PORT = _get_int_env("PORT", 3000)

    # ``FLASK_DEBUG`` toggle, consumed here under its EXACT env key name so the
    # active ``.env.example`` key maps 1:1 onto this configuration surface
    # (CP1 active-key parity). Truthy tokens (``1``/``true``/``yes``/``on``)
    # enable it. The base profile defaults it OFF (production-safe); the
    # per-environment subclasses below raise the *default* (development and
    # testing default ON) while still honouring an explicit environment override.
    # The ``flask run`` development server reads this same variable as well.
    FLASK_DEBUG = _get_bool_env("FLASK_DEBUG", False)

    # Flask's actual debug switch, derived DIRECTLY from ``FLASK_DEBUG`` so the
    # environment variable and ``app.config["DEBUG"]`` can never disagree. Under
    # gunicorn this class attribute governs ``app.config["DEBUG"]``.
    DEBUG = FLASK_DEBUG

    # Flask testing switch. OFF outside the testing profile; enables Flask's
    # testing behaviour (e.g. propagating exceptions to the caller) when True.
    TESTING = False

    # Preserve key insertion order in JSON responses instead of sorting keys
    # alphabetically. Kept ``False`` for stable, insertion-ordered output;
    # revisit for exact response-shape parity once the original server's JSON
    # behaviour is known.
    #
    # NOTE (Flask 3.x): the legacy ``JSON_SORT_KEYS`` config key is no longer
    # auto-honored by Flask -- the modern interface is ``app.json.sort_keys``.
    # The attribute is retained here as part of the documented configuration
    # surface; the application factory may translate it to
    # ``app.json.sort_keys = <cfg>.JSON_SORT_KEYS`` when exact JSON response
    # parity with the original is required.
    JSON_SORT_KEYS = False

    @staticmethod
    def init_app(app):
        """Per-configuration initialisation hook (a stable extension point).

        Invoked by the application factory after the configuration object has
        been loaded onto the app, to perform any environment-specific setup
        (for example configuring logging handlers or registering teardown
        callbacks). It is intentionally a no-op on the base class so the factory
        can always call ``selected_config.init_app(app)`` uniformly regardless
        of the active profile; subclasses (or future source-derived
        configuration) may override it to add behaviour.

        Args:
            app: The Flask application instance being configured.

        Returns:
            ``None``. The hook mutates ``app`` in place when overridden.
        """
        # No universal per-environment setup is required today. This deliberate
        # no-op keeps the factory's call site uniform across all profiles.
        return None


class DevelopmentConfig(Config):
    """Local development profile: verbose errors and the interactive debugger.

    Inherits every attribute and :meth:`Config.init_app` from :class:`Config`,
    raising the debug default (``FLASK_DEBUG`` / ``DEBUG``) to enable Flask's
    debugger (and, under ``flask run``, the auto-reloader). This is the profile
    that ``"default"`` resolves to (see :data:`CONFIG_MAP`).
    """

    # Development defaults the debugger ON, but an explicit ``FLASK_DEBUG=0`` in
    # the environment still wins (an explicit env value overrides the profile
    # default). ``DEBUG`` is kept identical to ``FLASK_DEBUG`` for consistency.
    FLASK_DEBUG = _get_bool_env("FLASK_DEBUG", True)
    DEBUG = FLASK_DEBUG


class ProductionConfig(Config):
    """Production profile: debugging disabled; secrets MUST come from the env.

    Inherits every attribute and :meth:`Config.init_app` from :class:`Config`.
    Production deployments MUST supply a strong, random ``SECRET_KEY`` via the
    environment -- the inherited placeholder default is unsafe for production and
    exists only for local-development convenience.
    """

    # Production defaults the debugger OFF. An explicit ``FLASK_DEBUG`` from the
    # environment is still honoured, but enabling the debugger in production is
    # strongly discouraged; the default (and recommended) value is
    # ``FLASK_DEBUG=0``. ``DEBUG`` is kept identical to ``FLASK_DEBUG``.
    FLASK_DEBUG = _get_bool_env("FLASK_DEBUG", False)
    DEBUG = FLASK_DEBUG


class TestingConfig(Config):
    """Automated-test profile used by the pytest suite (``create_app("testing")``).

    Inherits every attribute and :meth:`Config.init_app` from :class:`Config`.
    ``APP_CONFIG=testing`` and an explicit ``get_config("testing")`` both resolve
    here (see :data:`CONFIG_MAP`).
    """

    # Flag the application as under test so Flask propagates exceptions to the
    # client (instead of returning a 500) and test helpers behave correctly.
    TESTING = True

    # Keep the debugger on during tests for clearer tracebacks (an explicit
    # ``FLASK_DEBUG=0`` still wins). ``DEBUG`` is kept identical to
    # ``FLASK_DEBUG``. Additional testing-only toggles (for example an in-memory
    # database URI) are added one-to-one only when the original source introduces
    # the corresponding configuration -- never invented ahead of the source
    # (AAP Section 0.7).
    FLASK_DEBUG = _get_bool_env("FLASK_DEBUG", True)
    DEBUG = FLASK_DEBUG


# ---------------------------------------------------------------------------
# Selector map: public profile name -> Config class. The ``"default"`` alias
# points at :class:`DevelopmentConfig` so that a missing or unrecognised
# ``APP_CONFIG`` resolves to the safe local-development profile, consistent with
# ``.env.example`` (``APP_CONFIG=development``).
# ---------------------------------------------------------------------------
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(name=None):
    """Resolve and return the active configuration CLASS (not an instance).

    The application factory (``app/__init__.py``) calls this to obtain the class
    it then hands to ``app.config.from_object(...)``.

    Args:
        name: Optional explicit profile name -- one of ``"development"``,
            ``"production"``, ``"testing"``, or ``"default"``. When ``None``
            (the usual call from the factory), the profile is read from the
            ``APP_CONFIG`` environment variable, falling back to ``"default"``.
            Matching is case-insensitive and ignores surrounding whitespace.

    Returns:
        The selected :class:`Config` subclass. Unknown or unmatched names fall
        back to ``CONFIG_MAP["default"]`` so callers always receive a usable
        configuration class.

    Example:
        >>> get_config("testing").__name__
        'TestingConfig'
    """
    # Fall back to the APP_CONFIG environment variable when no explicit name is
    # provided (the factory typically calls get_config() or get_config(None)).
    if name is None:
        name = os.environ.get("APP_CONFIG", "default")

    # Normalise string inputs so "Production", " production ", "TESTING", etc.
    # all match their lower-case map keys.
    if isinstance(name, str):
        name = name.strip().lower()

    # Unknown / unmatched selectors degrade gracefully to the default profile
    # rather than raising, so a misconfigured environment still boots.
    return CONFIG_MAP.get(name, CONFIG_MAP["default"])


# Public API of this module: the config classes, the selector map, and the
# resolver function. Anything not listed here is an implementation detail.
__all__ = [
    "Config",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
    "CONFIG_MAP",
    "get_config",
]
