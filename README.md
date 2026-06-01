# Artifact2

A **Python 3 + [Flask](https://flask.palletsprojects.com/)** rewrite of an existing **Node.js** HTTP server. The goal of this project is **behavioral parity**: the Flask application is intended to reproduce *all* functionality of the original Node.js server — identical routes, middleware behavior, data models, configuration surface, and business rules — without adding, removing, or altering any externally observable behavior.

> ### ⚠️ Status / Prerequisite — read before contributing
>
> **The original Node.js source that this project ports is not present in this repository.** A faithful, functionality‑preserving port is defined entirely by the source it mirrors, so the **resource‑specific** parts of the application — the concrete endpoints, data models, services, validation schemas, and their tests — **cannot be implemented until the original Node.js source is supplied.**
>
> What exists today is a **runnable, source‑agnostic Flask foundation (scaffold)**: the application‑factory entrypoint, environment‑driven configuration, a shared‑extensions module, the WSGI entrypoint, a pinned dependency manifest, and the test scaffold. No endpoints, models, or business rules are documented here because none are known yet — and inventing any would violate the parity mandate (*"nothing is invented and nothing is dropped"*).
>
> **To complete the port:** add the original Node.js project to the repository (or provide it as an attachment). Each Express router, model, middleware, and `process.env.*` value then maps one‑to‑one onto its Flask equivalent (see [Porting Methodology](#porting-methodology)).

---

## Tech Stack

The application targets **Python 3** (recommended **≥ 3.12**; Flask 3.1.x requires Python ≥ 3.9) and is built on the following **core** stack. All versions are exact pins, verified against PyPI and declared in [`requirements.txt`](requirements.txt).

| Package | Version | Role | Replaces (Node.js) |
| --- | --- | --- | --- |
| [Flask](https://flask.palletsprojects.com/) | `3.1.3` | Web framework and routing | `express` |
| [gunicorn](https://gunicorn.org/) | `26.0.0` | Production WSGI server | `node` / `pm2` runtime |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `1.2.2` | Loads environment variables from `.env` | `dotenv` |
| [Flask-Cors](https://flask-cors.readthedocs.io/) | `6.0.2` | Cross‑origin resource sharing | `cors` |
| [pytest](https://docs.pytest.org/) | `9.0.3` | Test runner (dev/test) | `jest` / `mocha` / `supertest` |

Transitive libraries installed automatically with Flask — **Werkzeug, Jinja2, MarkupSafe, ItsDangerous, Click, and Blinker** — are governed by Flask's own version constraints and are intentionally not pinned separately.

**Additional libraries are added once the original `package.json` is known.** Drivers, ORMs, auth, validation, and other dependencies are selected to match exactly what the source used (they currently live as commented, inert candidates in `requirements.txt`). The substitutions follow a standard equivalence map — for example `express → Flask`, `mongoose → PyMongo`, `sequelize → SQLAlchemy`, `jsonwebtoken → PyJWT`, and `joi`/`express-validator → marshmallow`. The full map is in [Porting Methodology](#porting-methodology).

---

## Project Structure

The application follows the idiomatic Flask **application‑factory** pattern with **Blueprints**, a centralized configuration class, and a shared‑extensions module. The intended layout is shown below. Folders marked *“populated once the Node.js source is provided”* are **resource‑specific** and remain empty until the source is supplied; the rest form the foundation that is present (or bootable) today.

```text
.
├── wsgi.py                     # Production WSGI entrypoint: app = create_app()   [created with the app]
├── app/                        # Application package                              [created with the app]
│   ├── __init__.py             #   create_app() factory: config, extensions, blueprints, error handlers
│   ├── config.py               #   Env-driven Config classes (host, port, secrets, DB URI)
│   ├── extensions.py           #   Shared singletons (db, cors, jwt, limiter, ...)
│   ├── blueprints/             #   One Blueprint per original Express router (1:1)   ← populated once the Node.js source is provided
│   ├── models/                 #   Data models (SQLAlchemy or PyMongo)              ← populated once the Node.js source is provided
│   ├── services/               #   Business logic ported from controllers/services ← populated once the Node.js source is provided
│   ├── schemas/                #   Request/response validation & serialization     ← populated once the Node.js source is provided
│   ├── middleware/             #   hooks.py (before/after_request) + error_handlers.py
│   └── utils/                  #   Shared helpers (JWT, hashing, pagination, ...)
├── tests/                      # Test suite                                        [created with the app]
│   ├── conftest.py             #   Shared fixtures (app, test client, database)
│   ├── unit/                   #   Fast service/model unit coverage                ← populated once the Node.js source is provided
│   └── integration/            #   Endpoint/contract coverage reproducing originals ← populated once the Node.js source is provided
├── requirements.txt            # Pinned Python dependencies (core + commented conditional tier)
├── .env.example                # Documented template for every environment variable
├── pyproject.toml              # Tooling & test configuration (pytest, optional black/ruff)
└── .gitignore                  # Python ignore patterns (.venv, __pycache__, .env, ...)
```

> **Currently present:** `requirements.txt`, `.env.example`, `pyproject.toml`, `.gitignore`, and this `README.md`. The `wsgi.py` entrypoint, the `app/` package, and the `tests/` tree are part of the application‑implementation work and are created next; the **resource‑specific** modules within them are filled in one‑to‑one against the original source once it is supplied.

---

## Configuration

All configuration flows through **environment variables**, loaded at startup by `python-dotenv` and read by a `Config` class in `app/config.py`. **Secrets are never hardcoded.** Copy the documented template to a local `.env` and edit the values:

```bash
cp .env.example .env
# then edit .env to suit your environment
```

`.env` is git‑ignored; only the `.env.example` template is committed, and it holds placeholders and safe defaults only. The core, source‑agnostic variables it documents are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLASK_APP` | `wsgi.py` | Flask CLI entrypoint (used by `flask run`, `flask shell`) |
| `FLASK_DEBUG` | `0` | Development debugger + auto‑reloader toggle (never enable in production) |
| `APP_CONFIG` | `development` | Selects which `Config` class `app/config.py` activates |
| `SECRET_KEY` | *(placeholder)* | Signs session cookies / ItsDangerous tokens — set a strong random value locally |
| `HOST` | `0.0.0.0` | Network interface the server binds to |
| `PORT` | `3000` | TCP port the server listens on (mirrors the original `process.env.PORT`) |

Additional, source‑derived variables (for example a database URI, a JWT secret, or a CORS origin list) are kept commented and inert in `.env.example`; you uncomment and set exactly the ones the original project used once its source is supplied.

---

## Setup & Installation

The project uses a local virtual environment. From the repository root:

```bash
# 1. Create an isolated virtual environment
python -m venv .venv

# 2. Activate it
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (cmd)
# .venv\Scripts\Activate.ps1     # Windows (PowerShell)

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Create your local configuration from the template
cp .env.example .env
# edit .env as needed
```

---

## Running the Application

### Production

Run under **gunicorn**, the production WSGI server. The application object is exposed as `app` in `wsgi.py`:

```bash
# Simplest form
gunicorn wsgi:app

# With an explicit bind address and worker count (host/port mirror .env: HOST/PORT)
gunicorn --bind 0.0.0.0:3000 --workers 4 wsgi:app
```

> Flask's built‑in server is **for development only** and must not be used to serve production traffic.

### Development

Use the Flask development server, which provides the interactive debugger and auto‑reloader:

```bash
flask --app wsgi run --debug
```

Because `FLASK_APP=wsgi.py` is set in `.env`, a plain `flask run --debug` works as well. If `wsgi.py` includes a `__main__` block, `python wsgi.py` is an additional convenience entrypoint.

---

## Testing

Tests are written with **pytest**; the configuration (test paths, discovery rules, and `unit`/`integration` markers) lives in [`pyproject.toml`](pyproject.toml). From the repository root, with the virtual environment activated:

```bash
# Run the whole suite
pytest

# Run only the fast unit tests, or everything except integration tests
pytest -m unit
pytest -m "not integration"
```

The suite asserts **input/output parity** at both the unit level (services/models) and the integration level (HTTP routes), so that identical inputs produce identical outputs to the original server. Until the original behaviors are ported, the `tests/` tree is empty and a repository‑level `pytest` run collects no tests.

---

## Porting Methodology

Once the original Node.js project is supplied, the rewrite proceeds as a deterministic, **one‑to‑one** translation — every original construct maps to a single Flask equivalent, and the result is validated against the source for behavioral parity. The mapping is intentionally high‑level and source‑agnostic; concrete names and counts are finalized against the actual source files.

| Original Node.js construct | Target Flask equivalent |
| --- | --- |
| `app.js` / `server.js` / `index.js` bootstrap (`app.listen`) | `app/__init__.py` `create_app()` + `wsgi.py` |
| `express.Router()` modules | Blueprints in `app/blueprints/` registered via `register_blueprint()` (1:1 routes) |
| Global middleware (`app.use(...)`) | `before_request` / `after_request` hooks in `app/middleware/` + extensions |
| Route handlers / controllers | Flask view functions delegating to `app/services/` |
| Models (`mongoose` / `sequelize`) | `app/models/` via SQLAlchemy or PyMongo, bound in `app/extensions.py` |
| `process.env.*` usage | `app/config.py` attributes + `.env.example` entries |
| Error‑handling middleware (`(err, req, res, next)`) | `@app.errorhandler` registrations in `app/middleware/error_handlers.py` |

The library substitutions backing this mapping:

| Concern | Node.js | Python / Flask |
| --- | --- | --- |
| Framework / routing | `express` | Flask |
| Request body parsing | `body-parser` / `express.json` | Flask built‑in (`request.get_json`, `request.form`) |
| CORS | `cors` | Flask‑Cors |
| Environment config | `dotenv` | python‑dotenv |
| Token auth | `jsonwebtoken` | PyJWT |
| Password hashing | `bcrypt` / `bcryptjs` | bcrypt |
| MongoDB access | `mongoose` / `mongodb` | PyMongo (+ Flask‑PyMongo) |
| SQL access | `sequelize` / `knex` / `pg` / `mysql2` | SQLAlchemy (+ Flask‑SQLAlchemy) |
| Outbound HTTP | `axios` / `node-fetch` | requests |
| Realtime / websockets | `socket.io` | Flask‑SocketIO |
| Rate limiting | `express-rate-limit` | Flask‑Limiter |
| Validation / serialization | `joi` / `express-validator` | marshmallow |
| File uploads | `multer` | Werkzeug `request.files` |
| Logging | `morgan` / `winston` | Python `logging` |
| Testing | `jest` / `mocha` / `supertest` | pytest |

The port is considered complete only when, against the supplied source, every route is reachable at an identical method + path returning an equivalent status code and body; the environment‑variable surface, error responses, authentication, and persisted data shapes all match; and the pytest suite mirrors the original tests and passes.
