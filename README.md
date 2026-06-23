# workoutx-sdk — WorkoutX Fitness & Exercise API SDK for Python

[![PyPI version](https://img.shields.io/pypi/v/workoutx-sdk.svg)](https://pypi.org/project/workoutx-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/workoutx-sdk.svg)](https://pypi.org/project/workoutx-sdk/)
[![license](https://img.shields.io/pypi/l/workoutx-sdk.svg)](./LICENSE)

The official Python SDK for the [**WorkoutX API**](https://workoutxapp.com) —
1,300+ exercises with form GIFs, a workout generator, supplement intelligence, and AI
body-scan analysis, all behind one simple key. A modern Python
[ExerciseDB alternative](https://workoutxapp.com/exercisedb-alternative.html) for fitness apps.

> 🔑 **[Get a free API key](https://workoutxapp.com/dashboard.html)** · 🌐 **[workoutxapp.com](https://workoutxapp.com)** · 📚 **[API docs](https://workoutxapp.com/docs.html)**

Covers exercises, GIFs, workout generator, supplements, Body Scan, account, and billing
in one client. Python 3.8+. Only depends on `certifi` (for reliable TLS across platforms).

## Install

```bash
pip install workoutx-sdk
```

## Quick start

```python
from workoutx import WorkoutX

wx = WorkoutX(
    api_key="wx_your_key_here",   # exercises / gifs / workout / supplements
    scan_token="eyJ...",           # body scan (optional)
)

# Exercises
page    = wx.exercises.list(limit=20)
by_id   = wx.exercises.get("0001")
lunges  = wx.exercises.by_name("lunges")
similar = wx.exercises.similar("0001")
alts    = wx.exercises.alternatives("0001", equipment="dumbbell")

# GIFs
data = wx.gifs.get("0001")          # bytes
src  = wx.gif_url("0001")           # URL for <img>

# Workout & supplements
workout = wx.workout.generate(goal="hypertrophy", days=4)
stack   = wx.supplements.stack(goal="cut")

# Body Scan
credits = wx.scan.credits()
history = wx.scan.history(limit=10)

# Account & billing
login    = wx.auth.login("u@x.com", "•••")   # token cached for scan/auth/billing
me       = wx.auth.me()
keys     = wx.auth.list_keys()
sub      = wx.billing.status()
checkout = wx.billing.checkout("pro", "yearly")   # -> {"url": ...} to redirect to Stripe
```

## Authentication

| Product | Resources | Credential |
|---------|-----------|------------|
| Exercises | `exercises`, `gifs`, `workout`, `supplements` | `api_key` (`wx_...`) |
| Body Scan / Account / Billing | `scan.*`, `auth.*`, `billing.*` | Bearer JWT |

`auth`, `scan`, and `billing` share the same Bearer token — a successful
`auth.login()` caches it, so later `scan.*` / `billing.*` calls work without
re-supplying credentials. Google OAuth (`/v1/auth/google`) is a browser-redirect
flow and is intentionally not wrapped.

For Body Scan, pass a ready token or let the SDK log in for you:

```python
WorkoutX(api_key=key, scan_token="eyJ...")                       # ready token
WorkoutX(api_key=key, scan_email="u@x.com", scan_password="•")   # auto-login
```

## Avoiding the "name as ID" 404

`exercises.get(id)` needs an exact numeric ID (IDs have gaps). For names, use
`by_name`, or the resolver that tries an ID then falls back to a name search:

```python
ex = wx.exercises.find("lunges")   # dict | None
```

## Error handling

```python
from workoutx import WorkoutXError

try:
    wx.exercises.get("nope")
except WorkoutXError as e:
    e.status        # 404
    e.code          # "Not Found"
    e.tip           # hint from API, when present
    e.is_not_found  # plus is_auth_error, is_rate_limited
```

Transient failures (429, 5xx, network) are retried automatically with backoff,
honoring `Retry-After`.

## Development

```bash
pip install -e ".[test]"
pytest          # 25 offline unit tests (no network)
```

## About WorkoutX

[WorkoutX](https://workoutxapp.com) is a developer-first **fitness API** — a modern
**ExerciseDB alternative** that bundles everything you need to build workout, training,
and health apps behind a single key:

- 🏋️ **1,300+ exercises** with animated form **GIFs**, target & secondary muscles, equipment, and step-by-step instructions
- 🧠 **Workout generator** and multi-week training **programs**
- 💊 **Supplement intelligence** — recommended stacks per goal and per exercise
- 📸 **AI Body Scan** — body-fat %, measurements, and composition from photos
- 🔌 Clean REST API with **official SDKs** for JavaScript, Python, Flutter, and Swift

### Links

- 🌐 Website — https://workoutxapp.com
- 🔑 Get a free API key — https://workoutxapp.com/dashboard.html
- 📚 API documentation — https://workoutxapp.com/docs.html
- 🆚 ExerciseDB alternative — https://workoutxapp.com/exercisedb-alternative.html

### Official SDKs

- **JavaScript / TypeScript** — [`@workoutx/sdk`](https://www.npmjs.com/package/@workoutx/sdk) (npm)
- **Python** — [`workoutx-sdk`](https://pypi.org/project/workoutx-sdk/) (PyPI)
- **Flutter / Dart** — [`workoutx_sdk`](https://pub.dev/packages/workoutx_sdk) (pub.dev)
- **Swift** — [workoutx-sdk-swift](https://github.com/furkanuruk/workoutx-sdk-swift) (Swift Package Manager)

## License

MIT
