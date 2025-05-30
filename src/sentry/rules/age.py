from __future__ import annotations

import operator
from enum import StrEnum


class ModelAgeType(StrEnum):
    OLDEST = "oldest"
    NEWEST = "newest"


model_age_choices = [(ModelAgeType.OLDEST, "oldest"), (ModelAgeType.NEWEST, "newest")]


class AgeComparisonType(StrEnum):
    OLDER = "older"
    NEWER = "newer"


age_comparison_choices = [(AgeComparisonType.OLDER, "older"), (AgeComparisonType.NEWER, "newer")]
age_comparison_map = {AgeComparisonType.OLDER: operator.lt, AgeComparisonType.NEWER: operator.gt}
