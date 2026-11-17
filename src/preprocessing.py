"""Conservative job-description preprocessing.

The module cleans only text that is present in the source data.  It never
guesses, completes, expands, or otherwise infers missing job requirements.
"""

from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping
from typing import Any


JD_TEXT_FIELDS = (
    "Name",
    "Advertised_Title__c",
    "Job_Summary__c",
    "Rzlt__Key_Skills__c",
    "Rzlt__Required_Experience__c",
)

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def is_missing(value: object) -> bool:
    """Return whether a spreadsheet value represents missing text."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    # Handles pandas.NA without requiring pandas as a dependency.
    return value.__class__.__name__ == "NAType"


def clean_jd(raw_jd: object) -> str:
    """Return clean supplied JD text without changing its meaning.

    The function decodes HTML entities, removes HTML tags and non-printable
    control characters, then collapses whitespace. It intentionally retains
    punctuation, spelling, capitalization, product names, and technical terms.
    """
    if is_missing(raw_jd):
        return ""

    text = html.unescape(str(raw_jd))
    text = _HTML_TAG_PATTERN.sub(" ", text)
    text = _CONTROL_CHARACTER_PATTERN.sub(" ", text)
    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def preprocess_job(job: Mapping[str, Any]) -> str:
    """Build a clean JD from populated source fields only.

    Fields are joined in a stable order. Missing fields are omitted; no
    requirement is added when a source field is blank or unavailable.
    """
    cleaned_fields = [clean_jd(job.get(field)) for field in JD_TEXT_FIELDS]
    return "\n".join(text for text in cleaned_fields if text)


def main() -> None:
    """Print clean JDs from the default workbook for a quick manual check."""
    from data_loader import load_data

    _, jobs = load_data()
    for _, job in jobs.iterrows():
        print(preprocess_job(job))


if __name__ == "__main__":
    main()
