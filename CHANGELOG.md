# Changelog

All notable changes to this project are documented here. This project adheres
to [Semantic Versioning](https://semver.org/).

## 0.1.0

Initial release.

- Exercises: `list`, `get`, `byName`, `byBodyPart`, `byTarget`, `byEquipment`,
  `search`, `similar`, `alternatives`, `calories`, `changes`, `find`, and the
  `bodyPartList` / `targetList` / `equipmentList` / `secondaryMuscleList` lookups.
- GIFs: raw byte fetch and direct URL builder.
- Workout generator and supplement endpoints.
- Body Scan: credits, profile, history, key management, checkout, public packs.
- Account (`auth`): register, login, profile, API-key management, password
  reset, email verification, usage stats, and webhook configuration.
- Billing: subscription status, Stripe Checkout, and customer portal.
- Automatic retry with backoff on transient failures (429/5xx/network),
  honoring `Retry-After`.
- Shared Bearer token: a successful `auth.login()` is cached for later
  `scan` / `billing` calls.
