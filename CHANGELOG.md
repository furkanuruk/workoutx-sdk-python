# Changelog

All notable changes to this project are documented here. This project adheres
to [Semantic Versioning](https://semver.org/).

## Unreleased

- API v2 support (`v2`): the new exercise catalog (male and female models, 720p MP4 media at 30 fps), signed media links that expire, `freshMedia` to reuse or refresh links automatically, and `legacy` to map v1 exercise ids to v2. Not published until the v2 launch.

## Unreleased

### Fixed

- A `429` for an exhausted monthly quota (`X-Quota-Exceeded: true`) is no
  longer retried. It cannot succeed until the quota resets, so each retry was
  one more rejected request counted against the account. Rate-limit `429`s are
  still retried, but never after a `Retry-After` longer than 60 seconds.

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
