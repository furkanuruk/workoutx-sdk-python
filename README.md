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

## API v2

`wx.v2` is the new exercise catalog: 1,900+ movements as 2,700+ clips (male and
female models are separate exercises, linked by `counterpartId`), with 720p MP4
media at 30 fps. The API key is always sent in the `X-WorkoutX-Key` header.

Media links are signed and expire after about 24 hours: store exercise ids,
never media URLs, and call `fresh_media(id)` when you display an exercise. It
reuses the links of every exercise the SDK has already received (from `list`,
`get`, `similar`, `alternatives`, `workout.generate` and `workout.program`)
until they are close to expiry, and only then makes a request. Parameters keep
the API's camelCase names (`weightKg`, `bodyFocus`, `avoidJoints`, `daysPerWeek`).

```python
# Catalog. lang: en, tr, de, es, fr, zh-SG, zh-HK (filters stay English)
page    = wx.v2.list(body_part="chest", model="female", lang="de")
bench   = wx.v2.get("ex_SAWOOH", lang="tr")    # Barbell Bench Press
from_v1 = wx.v2.legacy("0025")                 # v1 id -> v2 exercise

# Similar exercises, alternatives and calories
similar = wx.v2.similar("ex_SAWOOH", limit=5)  # {exerciseId, model, total, limit, offset, results}
for ex in similar["results"]:
    print(ex["name"], ex["score"])             # full v2 exercises, best first
alts = wx.v2.alternatives("ex_SAWOOH", equipment="dumbbell", model="any")
kcal = wx.v2.calories("ex_SAWOOH", weightKg=80, minutes=20)   # kcal["totalKcal"]

# Workout sessions (lists are sent comma-separated)
session = wx.v2.workout.generate(
    goal="muscle_gain", duration=45, equipment="home",  # or ["dumbbell", "bench"]; presets gym, home, bodyweight
    split="upper", avoidJoints=["shoulder"], format="superset", model="female",
)
for step in session["warmup"]["items"]:
    print(step["exercise"]["name"], step["durationSeconds"])
for x in session["exercises"]:
    # block "C1" + "C2" = a superset; role: main, secondary, accessory, core, conditioning, mobility
    links = wx.v2.fresh_media(x["exercise"]["id"])  # no request: cached from generate()
    print(x["block"], x["exercise"]["name"], x["sets"], x.get("reps") or f'{x["durationSeconds"]}s',
          x.get("rir"), x["cue"], links and links["mp4"])

# Multi-week programs: exercises reference exerciseLibrary by id
program = wx.v2.workout.program(goal="strength", weeks=12, daysPerWeek=4, seed="plan-1")
library = {e["id"]: e for e in program["exerciseLibrary"]}
for week in program["program"]:
    for day in week["days"]:
        for x in day["exercises"]:
            print(week["week"], week["phase"], day["weekday"], library[x["exerciseId"]]["name"], x["sets"], x.get("reps"))

# Supplements (take v2 exercise ids)
supps = wx.v2.supplements.list(goal="strength", evidence="strong")
picks = wx.v2.supplements.for_exercise("ex_SAWOOH", limit=3)
stack = wx.v2.supplements.stack(goal="muscle_gain", level="essential")
```

A session (`workout.generate`) has a `summary`, a `warmup` (with `rampUp` sets
before the first main lift), `exercises` and a `cooldown`. Each exercise has a
`block` ("A", "B", "C1"/"C2" for a superset), `role`, movement `pattern`,
`sets`, `reps` or `durationSeconds`, `restSeconds`, `rir`, `tempo`, `load`, a
form `cue`, a `rationale` and light `alternatives` (no media: `wx.v2.get(id)`
them when the user swaps). Circuits add `circuit` timing and `rounds`. `goal`
takes `muscle_gain`, `strength`, `fat_loss`, `endurance`, `mobility` or
`general_fitness`; `duration` is 15 to 120 minutes; `avoidJoints` takes `knee`,
`shoulder`, `lumbar_spine`, `elbow`, `wrist`, `hip`, `ankle`; `format` is
`auto`, `straight`, `superset` or `circuit`.

A program (`workout.program`, 2 to 16 `weeks`, `seed` for a repeatable plan)
has a `schedule`, a `progressionModel`, `blocks` with deload weeks,
`weeklyVolume` per muscle group, the session templates (`sessions`) and the
weeks (`program`). Their exercises are light references by `exerciseId`; each
exercise appears once, with media, in `exerciseLibrary`, and `fresh_media`
reuses those links. Programs take no `split`, `bodyFocus` or `exclude`.

| Feature | Plans |
|---------|-------|
| `similar`, `alternatives`, `calories` | all plans |
| Joint & Rehab filters on `list` (`jointFocus`, `intensityLevel`, `movementTag`) | Growth, Scale (legacy Ultra) |
| `workout.generate`, `supplements.*` except `stack` | Growth, Scale (legacy Pro, Ultra) |
| `workout.program`, `supplements.stack` | Scale (legacy Ultra) |

On a plan without the feature, the call raises `WorkoutXError` with status
`403`; `e.body["requiredPlan"]` names the cheapest plan that has it.

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
pytest          # 44 offline unit tests (no network)
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
