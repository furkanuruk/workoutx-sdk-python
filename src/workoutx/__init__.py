"""Official Python SDK for the WorkoutX API."""
from .client import WorkoutX, DEFAULT_BASE_URL
from .errors import WorkoutXError, WorkoutXConnectionError
from .resources import (
    ExercisesResource,
    GifsResource,
    WorkoutResource,
    SupplementsResource,
    ScanResource,
    AuthResource,
    BillingResource,
)

__version__ = "0.1.0"
__all__ = [
    "WorkoutX",
    "DEFAULT_BASE_URL",
    "WorkoutXError",
    "WorkoutXConnectionError",
    "ExercisesResource",
    "GifsResource",
    "WorkoutResource",
    "SupplementsResource",
    "ScanResource",
    "AuthResource",
    "BillingResource",
]
