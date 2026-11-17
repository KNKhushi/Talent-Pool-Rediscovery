"""Load and validate the candidate and job data from the source workbook.

This module deliberately contains no AI or matching logic.  It is the small,
reliable boundary between the Excel source file and the DataFrames used by
later pipeline steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK_PATH = PROJECT_ROOT / "data" / "AI - Contacts & job.xlsx"
CONTACTS_SHEET = "Contacts"
JOBS_SHEET = "Job"
CV_COLUMN = "Rzlt__Text_CV__c"

# These are the fields used to describe a role for later matching work.
IMPORTANT_JD_FIELDS = (
    "Name",
    "Advertised_Title__c",
    "Job_Summary__c",
    "Rzlt__Location__c",
    "Rzlt__Key_Skills__c",
    "Rzlt__Required_Experience__c",
    "Rzlt__Minimum_Salary__c",
    "Rzlt__Maximum_Salary__c",
    "Rzlt__No_of_openings__c",
)


@dataclass(frozen=True)
class DataQualityReport:
    """Summary of the checks performed on the source worksheets."""

    candidate_count: int
    job_count: int
    contact_columns: list[str]
    job_columns: list[str]
    missing_cv_count: int
    missing_cv_row_numbers: list[int]
    important_jd_fields: dict[str, int | None]

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the report."""
        return {
            "candidate_count": self.candidate_count,
            "job_count": self.job_count,
            "contact_columns": self.contact_columns,
            "job_columns": self.job_columns,
            "missing_cv_count": self.missing_cv_count,
            "missing_cv_row_numbers": self.missing_cv_row_numbers,
            "important_jd_fields": self.important_jd_fields,
        }


def load_data(workbook_path: str | Path = DEFAULT_WORKBOOK_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the Contacts and Job worksheets into separate DataFrames.

    Values are read as objects so IDs, phone numbers, and postal codes retain
    their source representation rather than being unintentionally coerced.
    """
    source = Path(workbook_path)
    if not source.is_file():
        raise FileNotFoundError(f"Workbook not found: {source}")

    try:
        contacts = pd.read_excel(source, sheet_name=CONTACTS_SHEET, dtype=object)
        jobs = pd.read_excel(source, sheet_name=JOBS_SHEET, dtype=object)
    except ValueError as exc:
        raise ValueError(
            f"Workbook must contain '{CONTACTS_SHEET}' and '{JOBS_SHEET}' worksheets."
        ) from exc

    return contacts, jobs


def verify_data(contacts: pd.DataFrame, jobs: pd.DataFrame) -> DataQualityReport:
    """Check candidate CV coverage and the availability of core job fields."""
    if CV_COLUMN not in contacts.columns:
        raise KeyError(f"Contacts worksheet is missing the CV column: {CV_COLUMN}")

    cv_values = contacts[CV_COLUMN]
    missing_cv = cv_values.isna() | cv_values.astype(str).str.strip().eq("")
    # Add one because DataFrame index 0 corresponds to Excel row 2 (after headers).
    missing_cv_rows = (contacts.index[missing_cv] + 2).tolist()

    jd_field_status: dict[str, int | None] = {}
    for field in IMPORTANT_JD_FIELDS:
        if field not in jobs.columns:
            jd_field_status[field] = None
            continue
        values = jobs[field]
        jd_field_status[field] = int(values.isna().sum() + values.astype(str).str.strip().eq("").sum())

    return DataQualityReport(
        candidate_count=len(contacts),
        job_count=len(jobs),
        contact_columns=contacts.columns.tolist(),
        job_columns=jobs.columns.tolist(),
        missing_cv_count=int(missing_cv.sum()),
        missing_cv_row_numbers=missing_cv_rows,
        important_jd_fields=jd_field_status,
    )


def print_report(report: DataQualityReport) -> None:
    """Print a compact, human-readable verification summary."""
    print(f"Candidates: {report.candidate_count}")
    print(f"Jobs: {report.job_count}")
    print(f"Missing CVs: {report.missing_cv_count}")
    if report.missing_cv_row_numbers:
        print(f"Missing CV Excel rows: {report.missing_cv_row_numbers}")

    print("\nContacts columns:")
    print(", ".join(report.contact_columns))
    print("\nJob columns:")
    print(", ".join(report.job_columns))
    print("\nImportant JD fields (missing values; None means the column is absent):")
    for field, missing_count in report.important_jd_fields.items():
        print(f"- {field}: {missing_count}")


def main() -> None:
    """Load the default workbook and print its initial verification checks."""
    contacts, jobs = load_data()
    print_report(verify_data(contacts, jobs))


if __name__ == "__main__":
    main()
