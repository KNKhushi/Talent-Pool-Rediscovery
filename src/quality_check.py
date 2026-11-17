
from src.data_loader import load_data
import pandas as pd


def get_value(job, columns):
    """Return the first available non-empty value from the given columns."""
    for column in columns:
        if hasattr(job, "get"):
            value = job.get(column)
        else:
            value = None

        if value is None:
            continue

        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass

        if str(value).strip():
            return value

    return None


def check_jd_quality(job):
    """Validate required and optional job description fields."""

    fields = {
        "Job Title": (("Advertised_Title__c", "Name"), True),
        "Job Summary": (("Job_Summary__c",), True),
        "Key Skills": (("Rzlt__Key_Skills__c",), True),
        "Required Experience": (
            ("Rzlt__Required_Experience__c",),
            False,
        ),
        "Location": (("Rzlt__Location__c",), False),
        "Domain / Industry": (("Client_Industry__c",), False),
        "Role Level": (("Role_Level__c",), False),
        "Priority": (("Priority__c",), False),
        "Minimum Salary": (("Rzlt__Minimum_Salary__c",), False),
        "Maximum Salary": (("Rzlt__Maximum_Salary__c",), False),
        "Number of Openings": (
            ("Rzlt__No_of_openings__c", "Number_of_Openings"),
            True,
        ),
        "Salary Description": (("Rzlt__Salary_Description__c",), False),
        "Advertising Details": (
            (
                "Advertising_Bullet_Point_1__c",
                "Advertising_Bullet_Point_2__c",
                "Advertising_Bullet_Point_3__c",
            ),
            False,
        ),
    }

    results = {}

    for label, (columns, required) in fields.items():
        value = get_value(job, columns)

        if value is None:
            if required:
                results[label] = "MISSING - Required field"
            continue

        results[label] = f"Available - {value}"

    return results


def main():
    _, jobs_df = load_data()

    if jobs_df.empty:
        print("No job records found.")
        return

    for _, job in jobs_df.iterrows():
        results = check_jd_quality(job)

        title = get_value(job, ("Advertised_Title__c", "Name"))

        print("\n===== JD QUALITY CHECK =====")
        print(f"Job: {title or 'Unnamed job'}")

        for field, status in results.items():
            print(f"{field}: {status}")

        required_missing = [
            field
            for field, status in results.items()
            if status.startswith("MISSING - Required field")
        ]

        print("\n===== QUALITY SUMMARY =====")

        if required_missing:
            print("Missing required fields:", ", ".join(required_missing))
        else:
            print("All required fields are available.")


if __name__ == "__main__":
    main()
