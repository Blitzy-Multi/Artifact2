'use strict';

/**
 * server.js
 * -----------------------------------------------------------------------------
 * Express application entry point for the Artifact2 tutorial server.
 *
 * This minimal server demonstrates how to host HTTP GET endpoints with Express:
 *   - GET /              -> responds with the exact string "Hello world"
 *   - GET /good-evening  -> responds with the exact string "Good evening"
 *
 * The module uses CommonJS (`require`) — consistent with the project manifest
 * which intentionally omits `"type": "module"`. It is referenced by
 * package.json via the `main` field and the `start` script (`node server.js`).
 *
 * Source of behavior cited by README.md: this file (route handlers) and
 * package.json (start script / dependency declaration).
 */

// Import the Express framework (declared as a dependency in package.json: express ^5.2.1).
const express = require('express');

// Instantiate the Express application.
const app = express();

/**
 * Security hardening: do not advertise the framework in responses.
 *
 * Express sets an `X-Powered-By: Express` response header by default. Disabling
 * it removes that fingerprinting header from every response. This uses a
 * built-in Express application setting (`app.disable`) — it introduces no
 * dependency and no middleware.
 */
app.disable('x-powered-by');

/**
 * Listening port.
 *
 * Defaults to 3000 (the de facto Express tutorial convention) and is
 * overridable via the PORT environment variable so the server can be run in
 * environments that inject a port at runtime.
 */
const PORT = process.env.PORT || 3000;

/**
 * Method guard — serve only HTTP GET.
 *
 * The behavioral contract for this server is exactly two GET endpoints
 * (`GET /` and `GET /good-evening`). Express otherwise answers HEAD and OPTIONS
 * for GET routes implicitly, which would expose HTTP method responses beyond
 * those two routes. This guard runs before the route handlers — and before the
 * router's implicit HEAD/OPTIONS handling — so every non-GET request (HEAD,
 * OPTIONS, POST, PUT, PATCH, DELETE, ...) receives a 404 and only GET requests
 * reach the routes below.
 */
app.use((req, res, next) => {
  if (req.method !== 'GET') {
    return res.sendStatus(404);
  }
  next();
});

/**
 * Baseline endpoint.
 * GET / -> "Hello world"
 *
 * Returns the verbatim greeting string as a plain text response body.
 */
app.get('/', (req, res) => {
  res.send('Hello world');
});

/**
 * New endpoint (the feature requested for this change).
 * GET /good-evening -> "Good evening"
 *
 * Returns the verbatim greeting string as a plain text response body.
 */
app.get('/good-evening', (req, res) => {
  res.send('Good evening');
});

/**
 * Start the HTTP server and begin accepting connections.
 *
 * The callback logs the listening URL so a developer following the tutorial
 * can immediately see where to send requests.
 */
app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`Server is listening on http://localhost:${PORT}`);
});
