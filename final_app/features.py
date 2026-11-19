"""
Shared feature helpers used by the risk engine.
"""

import numpy as np

POSITIVE = "Positive"
NEGATIVE = "Negative"
INCONCLUSIVE = "Inconclusive"

_POSITIVE_VALUES = {"positive", "pos", "present", "detected", "true", "yes", "1"}
_NEGATIVE_VALUES = {"negative", "neg", "absent", "not_detected", "normal", "false", "no", "0"}
_INCONCLUSIVE_VALUES = {"inconclusive", "uncertain", "unknown", "pending", "indeterminate"}


def normalize_marker_status(value) -> str:
    """
    Normalize a genetic marker value into "Positive", "Negative" or "Inconclusive".

    Accepts booleans (from the form checkboxes), numpy booleans and common
    string spellings (e.g. from a CSV or lab report). Anything unrecognised,
    including None, is treated as "Negative".
    """
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _POSITIVE_VALUES:
            return POSITIVE
        if v in _NEGATIVE_VALUES:
            return NEGATIVE
        if v in _INCONCLUSIVE_VALUES:
            return INCONCLUSIVE
        return NEGATIVE

    if isinstance(value, (bool, np.bool_)):
        return POSITIVE if value else NEGATIVE

    return NEGATIVE
