# Changelog

All notable changes to this project are documented here. This project adheres
to [Semantic Versioning](https://semver.org/).

## 0.2.0

- API v2 support (`v2`): the new exercise catalog (male and female models, 720p MP4 media at 30 fps), signed media links that expire, `freshMedia` to reuse or refresh links automatically, and `legacy` to map v1 exercise ids to v2. Not published until the v2 launch.
- API v2 smart, workout and supplement methods: `v2.similar`, `v2.alternatives` and `v2.calories`; `v2.workout.generate` and `v2.workout.program`; `v2.supplements` (`list`, `filters`, `get`, `for_exercise`, `stack`) on v2 exercise ids. Exercises in similar, alternatives and workout results fill the media cache, so `fresh_media` reuses their links. Lists for `equipment`, `bodyFocus` and `exclude` are sent comma-separated. `lang` (`en`, `tr`, `de`, `es`, `fr`, `zh-SG`, `zh-HK`) on `list`, `get`, `legacy` and the new methods, and the Joint & Rehab filters (`jointFocus`, `intensityLevel`, `movementTag`) on `list`.
- v2 workouts: pattern-based sessions with warm-up/cool-down, supersets/circuits, joint care (`avoidJoints`), and programs with periodisation, deloads and an exercise library. New params `avoidJoints` (a list is sent comma-separated) and `format`, goal `general_fitness`, the `_b`/`_c` split variants, `duration` from 15 minutes, and `seed` and up to 16 `weeks` for programs. Warm-up, main and cool-down exercises of a session and a program's `exerciseLibrary` fill the media cache, so `fresh_media` reuses their links.


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
