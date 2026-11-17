"""Classify a job description into a broad, explainable business domain.

This is the first stage of the JD enrichment flow:

    JD -> Domain Classification -> Keyword Extraction

The classifier is deliberately rule-based so every classification can be
inspected and refined as the talent-pool workflow grows.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import re
from typing import Any


JOB_TEXT_FIELDS = (
    "Name",
    "Advertised_Title__c",
    "Job_Summary__c",
    "Rzlt__Key_Skills__c",
    "Rzlt__Required_Experience__c",
    "Client_Industry__c",
)

# Keep terms specific enough to be useful evidence.  Add new domains and terms
# here as the job catalogue expands.
DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Software Development": (
        "software engineer",
        "software developer",
        "full stack",
        "frontend",
        "back end",
        "backend",
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "node.js",
        "devops",
        "cloud engineer",
        "data engineer",
        "machine learning",
    ),
    "Finance": (
        "accountant",
        "accounting",
        "financial analyst",
        "finance manager",
        "bookkeeping",
        "bookkeeper",
        "payroll",
        "audit",
        "taxation",
        "budgeting",
        "accounts payable",
        "accounts receivable",
    ),
    "Human Resources": (
        "human resources",
        "hr manager",
        "hr business partner",
        "talent acquisition",
        "recruitment",
        "recruiter",
        "people and culture",
        "employee relations",
        "workforce planning",
        "learning and development",
    ),
    "Sales": (
        "sales representative",
        "sales executive",
        "account executive",
        "business development",
        "sales manager",
        "salesforce",
        "lead generation",
        "territory sales",
    ),
    "Marketing": (
        "marketing manager",
        "digital marketing",
        "content marketing",
        "seo",
        "social media",
        "brand manager",
        "campaign manager",
        "google ads",
    ),
    "Administration & Operations": (
        "executive assistant",
        "administrative assistant",
        "office manager",
        "office administrator",
        "personal assistant",
        "operations manager",
        "coordinator",
        "receptionist",
        "customer service",
    ),
    "Healthcare": (
        "registered nurse",
        "clinical",
        "healthcare",
        "medical",
        "patient care",
        "pharmacist",
        "physiotherapist",
        "aged care",
    ),
    "Engineering": (
        "mechanical engineer",
        "civil engineer",
        "electrical engineer",
        "structural engineer",
        "engineering manager",
        "autocad",
        "construction engineer",
    ),
    "Education": (
        "teacher",
        "educator",
        "lecturer",
        "curriculum",
        "school",
        "university",
        "training facilitator",
    ),
}


@dataclass(frozen=True)
class DomainClassification:
    """The domain label and the evidence used to assign it."""

    domain: str
    confidence: float
    matched_keywords: tuple[str, ...]


def _normalise_text(value: object) -> str:
    """Convert a spreadsheet value to usable text while treating blanks as empty."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def build_job_text(job: Mapping[str, Any]) -> str:
    """Combine the useful JD fields into one normalized classification input."""
    return "\n".join(
        value for field in JOB_TEXT_FIELDS if (value := _normalise_text(job.get(field)))
    )


def classify_domain(job_description: str) -> DomainClassification:
    """Classify JD text using matching domain keywords.

    Returns ``Unclassified`` when the text does not contain sufficiently
    specific evidence.  The confidence is a transparent score based only on
    the number of unique matching terms, capped below 1.0 for this heuristic.
    """
    normalized = job_description.casefold()
    scores: dict[str, list[str]] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        matches = [
            keyword
            for keyword in keywords
            if re.search(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)", normalized)
        ]
        if matches:
            scores[domain] = matches

    if not scores:
        return DomainClassification("Unclassified", 0.0, ())

    domain, matches = max(scores.items(), key=lambda item: len(item[1]))
    confidence = min(0.95, round(0.40 + 0.15 * len(matches), 2))
    return DomainClassification(domain, confidence, tuple(matches))


def classify_job(job: Mapping[str, Any]) -> DomainClassification:
    """Classify one job record from its title, JD, skills, and related fields."""
    return classify_domain(build_job_text(job))


def main() -> None:
    """Classify every job in the default workbook as a quick manual check."""
    from src.data_loader import load_data 

    _, jobs = load_data()
    for _, job in jobs.iterrows():
        result = classify_job(job)
        print(f"{job.get('Name', 'Unnamed job')}: {result.domain}")
        print(f"  confidence={result.confidence}; evidence={list(result.matched_keywords)}")


if __name__ == "__main__":
    main()
