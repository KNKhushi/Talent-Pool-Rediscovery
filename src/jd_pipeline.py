
import json
from pathlib import Path

import pandas as pd

from src.preprocessing import preprocess_job, clean_jd
from src.domain_classifier import classify_domain
from src.keyword_extraction import extract_keywords
from src.embeddings import embed_text
from src.quality_check import check_jd_quality


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "results" / "jd_output.json"


def safe_text(value):
    """Clean text and return None if it is empty."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = clean_jd(str(value))
    return text if text else None


def parse_openings(value):
    """Return a positive integer for the number of openings, or None."""
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        openings = int(value)
        return openings if openings > 0 else None
    except (ValueError, TypeError):
        return None


def main():
    print("\n========== JOB DESCRIPTION INPUT ==========")

    job_title = input("Enter job title: ").strip()
    job_description = input("Enter job description: ").strip()
    required_skills = input(
        "Enter required skills, separated by commas: "
    ).strip()
    required_experience = input(
        "Enter required experience (optional): "
    ).strip()
    qualifications = input(
        "Enter required qualifications (optional): "
    ).strip()
    location = input("Enter job location (optional): ").strip()

    openings_input = input(
        "Enter number of openings (positive whole number): "
    ).strip()
    number_of_openings = parse_openings(openings_input)

    if not job_title and not job_description and not required_skills:
        print("Please enter a job title, description, or required skills.")
        return

    if number_of_openings is None:
        print(
            "Invalid number of openings. Please enter a positive whole "
            "number, such as 1 or 2."
        )
        return

    # Build a job record compatible with the existing preprocessing code.
    job = {
        "Name": job_title,
        "Advertised_Title__c": job_title,
        "Job_Summary__c": job_description,
        "Rzlt__Key_Skills__c": required_skills,
        "Rzlt__Required_Experience__c": required_experience,
        "Rzlt__Location__c": location,
        "Extracted_Qualifications": qualifications,
        "Number_of_Openings": number_of_openings,
    }

    # Process the job description.
    cleaned_job = safe_text(preprocess_job(job)) or ""

    if not cleaned_job:
        print("Could not prepare the job description.")
        return

    # Classify the job domain and extract keywords.
    domain_result = classify_domain(cleaned_job)
    keywords = extract_keywords(cleaned_job)

    # Remove duplicate keywords and generic title words.
    title_words = set(job_title.casefold().split())
    filtered_keywords = []
    seen = set()

    for keyword in keywords:
        keyword = str(keyword).strip()
        normalized = keyword.casefold()

        if not normalized or normalized in seen:
            continue

        if len(normalized.split()) == 1 and normalized in title_words:
            continue

        filtered_keywords.append(keyword)
        seen.add(normalized)

    # Generate semantic embeddings.
    embedding = embed_text(cleaned_job)

    # Check JD quality.
    quality = check_jd_quality(job)

    if hasattr(quality, "as_dict"):
        quality = quality.as_dict()

    if not isinstance(quality, dict):
        quality = {"status": str(quality)}

    source_fields = {
        "job_title": safe_text(job_title),
        "job_summary": safe_text(job_description),
        "key_skills": safe_text(required_skills),
        "required_experience": safe_text(required_experience),
        "qualifications": safe_text(qualifications),
        "location": safe_text(location),
        "number_of_openings": number_of_openings,
    }

    result = {
        "job_title": job_title or None,
        "domain": domain_result.domain,
        "domain_confidence": domain_result.confidence,
        "domain_evidence": list(domain_result.matched_keywords),
        "cleaned_job_text": cleaned_job,
        "keywords": filtered_keywords,
        "required_skills": [
            item.strip()
            for item in required_skills.replace(";", ",").split(",")
            if item.strip()
        ],
        "required_experience": required_experience or None,
        "qualifications": qualifications or None,
        "number_of_openings": number_of_openings,
        "embedding_dimension": len(embedding),
        "embedding": [float(value) for value in embedding],
        "source_fields": source_fields,
        "quality_check": quality,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== JD PIPELINE RESULT ==========")
    print("Job title:", result["job_title"])
    print("Domain:", result["domain"])
    print("Domain confidence:", result["domain_confidence"])
    print("Keywords:", filtered_keywords)
    print("Required skills:", result["required_skills"])
    print("Required experience:", result["required_experience"])
    print("Qualifications:", result["qualifications"])
    print("Number of openings:", result["number_of_openings"])
    print("Embedding dimension:", len(embedding))

    # Display the essential JD validation.
    required_fields = {
        "Job Title": job_title,
        "Job Summary": job_description,
        "Key Skills": required_skills,
        "Number of Openings": str(number_of_openings),
    }

    available_fields = [
        field
        for field, value in required_fields.items()
        if value.strip()
    ]

    missing_fields = [
        field
        for field, value in required_fields.items()
        if not value.strip()
    ]

    print("\n========== JD QUALITY CHECK ==========")
    print(
        "JD validation:",
        "Passed" if not missing_fields else "Needs review",
    )

    if available_fields:
        print("Available information:", ", ".join(available_fields))

    if missing_fields:
        print("Missing fields:", ", ".join(missing_fields))

    # Report any additional issues identified by the project's quality checker.
    if quality:
        print("\nDetailed quality-check result:")
        print(json.dumps(quality, indent=2, ensure_ascii=False))

    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
