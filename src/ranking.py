
import re


UNKNOWN_VALUES = {
    "",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "not specified",
    "needs review",
    "unknown",
}


def _experience_fit(candidate_experience, required_experience):
    """Calculate experience fit and return a review status."""

    candidate_value = str(
        candidate_experience or ""
    ).casefold().strip()
    required_value = str(
        required_experience or ""
    ).casefold().strip()

    if candidate_value in UNKNOWN_VALUES:
        return 0.5, "Unknown - candidate experience unavailable"

    number_pattern = r"\d+(?:\.\d+)?"
    candidate_numbers = re.findall(
        number_pattern, candidate_value
    )
    required_numbers = re.findall(
        number_pattern, required_value
    )
    if not candidate_numbers:
        return 0.5, "Unknown - experience could not be interpreted"

    candidate_years = float(candidate_numbers[0])

    # A non-numeric JD preference is not a minimum or bounded range.
    if required_value in UNKNOWN_VALUES or not required_numbers:
        return (
            0.5,
            "No numeric JD experience minimum; candidate experience recorded",
        )

    minimum_years = float(required_numbers[0])
    range_pattern = (
        r"\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?"
    )
    is_bounded_range = re.search(
        range_pattern, required_value
    )
    if is_bounded_range and len(required_numbers) >= 2:
        maximum_years = float(required_numbers[1])
        if maximum_years < minimum_years:
            return 0.5, "Unknown - JD experience range is invalid"
        if candidate_years < minimum_years:
            if minimum_years <= 0:
                return 1.0, "Meets required experience"
            return (
                min(candidate_years / minimum_years, 1.0),
                "Below JD minimum - recruiter verification needed",
            )
        if candidate_years > maximum_years:
            return (
                0.5,
                "Exceeds stated JD experience range - recruiter review",
            )
        return 1.0, "Meets JD experience range"

    if minimum_years <= 0:
        return 1.0, "Meets required experience"
    if candidate_years < minimum_years:
        return (
            min(candidate_years / minimum_years, 1.0),
            "Below JD minimum - recruiter verification needed",
        )

    return 1.0, "Meets or exceeds JD minimum"


def rank_candidates(candidates):
    """
    Rank candidates primarily by evidence-backed skill coverage.

    Weights:
        Direct skill coverage: 60%
        Related skill coverage: 10%
        Semantic similarity: 10%
        Domain alignment: 10%
        Experience fit: 10%

    The ranking score is a comparison index, not a hiring probability.
    """

    if not candidates:
        return []

    for candidate in candidates:
        semantic_score = float(
            candidate.get("Semantic_Similarity", 0.0) or 0.0
        )

        direct_coverage = max(
            0.0,
            min(
                float(
                    candidate.get(
                        "Direct_Skill_Coverage",
                        candidate.get("Requirement_Coverage", 0.0),
                    )
                    or 0.0
                ),
                1.0,
            ),
        )

        related_coverage = max(
            0.0,
            min(
                float(
                    candidate.get("Related_Skill_Coverage", 0.0) or 0.0
                ),
                1.0,
            ),
        )

        domain_value = str(
            candidate.get("Candidate_Domain", "")
        ).casefold().strip()

        required_domain = str(
            candidate.get("Required_Domain", "")
        ).casefold().strip()

        if (
            domain_value in UNKNOWN_VALUES
            or required_domain in UNKNOWN_VALUES
        ):
            domain_score = 0.5
        else:
            domain_score = float(
                bool(candidate.get("Domain_Match", False))
            )

        experience_score, experience_status = _experience_fit(
            candidate.get("Years_of_Experience", ""),
            candidate.get("Required_Experience", ""),
        )

        candidate["Experience_Match_Status"] = experience_status

        review_flags = []

        if experience_status.startswith("Unknown"):
            review_flags.append(experience_status)
        elif experience_status.startswith("Below JD minimum"):
            review_flags.append(experience_status)
        elif experience_status.startswith(
            "Exceeds stated JD experience range"
        ):
            review_flags.append(experience_status)

        domain_status = str(
            candidate.get("Domain_Match_Status", "Unknown")
        ).casefold().strip()

        if domain_status == "unknown":
            review_flags.append(
                "Domain match unknown - verify candidate domain"
            )

        qualifications = str(
            candidate.get("Qualifications", "")
        ).casefold().strip()

        if (
            qualifications in UNKNOWN_VALUES
            or qualifications == "not verified"
        ):
            review_flags.append(
                "Qualifications unavailable - verify with candidate"
            )

        candidate["Review_Flags"] = "; ".join(review_flags)

        # Calculate weighted contributions.
        direct_contribution = 0.60 * direct_coverage
        related_contribution = 0.10 * related_coverage

        semantic_contribution = 0.10 * max(
            0.0,
            min(semantic_score, 1.0),
        )

        domain_contribution = 0.10 * domain_score
        experience_contribution = 0.10 * experience_score

        ranking_score = (
            direct_contribution
            + related_contribution
            + semantic_contribution
            + domain_contribution
            + experience_contribution
        )

        # Store the ranking score on a 0-100 scale.
        candidate["Ranking_Score"] = round(
            max(0.0, min(ranking_score, 1.0)) * 100,
            2,
        )

        score = candidate["Ranking_Score"]
        experience_needs_review = (
            experience_status.startswith("Unknown")
            or experience_status.startswith("Below JD minimum")
            or experience_status.startswith(
                "Exceeds stated JD experience range"
            )
        )
        if (
            score >= 75
            and direct_coverage >= 0.70
            and not experience_needs_review
        ):
            recommendation = "Highly Recommended"
        elif (
            score >= 60
            and direct_coverage >= 0.40
            and not experience_needs_review
        ):
            recommendation = "Recommended"
        elif score >= 40:
            recommendation = "Needs Review"
        else:
            recommendation = "Not Recommended"
        candidate["Recommendation_Status"] = recommendation

        requirement_count = float(
            candidate.get("Requirement_Count", 0) or 0
        )

        related_count = round(related_coverage * requirement_count)
        direct_count = round(direct_coverage * requirement_count)

        candidate["Ranking_Explanation"] = (
            f"Comparison score {candidate['Ranking_Score']:.2f}/100 "
            "(not a probability): "
            f"direct evidence for {direct_count} requirement(s) "
            f"contributes {direct_contribution * 100:.1f} points; "
            f"related evidence for {related_count} requirement(s) "
            f"contributes {related_contribution * 100:.1f} points; "
            f"semantic similarity {semantic_score:.2f} contributes "
            f"{semantic_contribution * 100:.1f} points; "
            f"domain status "
            f"{candidate.get('Domain_Match_Status', 'Unknown')} "
            f"contributes {domain_contribution * 100:.1f} points; "
            f"experience status '{experience_status}' contributes "
            f"{experience_contribution * 100:.1f} points."
        )

        if direct_coverage >= 0.70:
            candidate["Recruiter_Review_Priority"] = (
                "Strong evidence - recruiter review"
            )
        elif direct_coverage >= 0.40:
            candidate["Recruiter_Review_Priority"] = (
                "Partial evidence - recruiter review"
            )
        else:
            candidate["Recruiter_Review_Priority"] = (
                "Insufficient evidence - lower priority; "
                "not automatically rejected"
            )

        matched_skills = str(
            candidate.get("Matched_Keywords", "")
        ).strip()
        missing_skills = str(
            candidate.get("Missing_JD_Requirements", "")
        ).strip()
        related_evidence = str(
            candidate.get("Related_Evidence", "")
        ).strip()
        potential_gaps = str(
            candidate.get("Potential_Gaps", "")
        ).strip()
        candidate_experience = str(
            candidate.get("Years_of_Experience", "")
        ).strip()
        domain_status_display = str(
            candidate.get("Domain_Match_Status", "Unknown")
        ).strip()
        candidate_domain = str(
            candidate.get("Candidate_Domain", "Unknown")
        ).strip()
        required_domain_display = str(
            candidate.get("Required_Domain", "Unknown")
        ).strip()
        qualification_details = str(
            candidate.get("Qualifications", "Not verified")
        ).strip()

        reason_parts = []
        reason_parts.append(f"Recommendation status: {recommendation}.")
        if matched_skills:
            reason_parts.append(
                f"Direct matching skill evidence: {matched_skills}."
            )
        else:
            reason_parts.append(
                "No direct matching skill evidence was identified."
            )

        reason_parts.append(
            f"Direct skill coverage: {direct_coverage:.0%} "
            f"({direct_count} requirement(s)); related skill coverage: "
            f"{related_coverage:.0%} ({related_count} requirement(s))."
        )
        if related_evidence:
            reason_parts.append(
                f"Potentially related evidence requiring verification: "
                f"{related_evidence}."
            )
        reason_parts.append(
            f"Requirements not identified in the available data: "
            f"{missing_skills or 'none listed'}; this does not prove the "
            "candidate lacks those skills."
        )
        if potential_gaps and potential_gaps.casefold() not in UNKNOWN_VALUES:
            reason_parts.append(f"Additional evidence note: {potential_gaps}")

        if candidate_experience.casefold() in UNKNOWN_VALUES:
            candidate_experience = "unknown"
        reason_parts.append(
            f"Candidate experience: {candidate_experience}; "
            f"assessment: {experience_status}."
        )
        reason_parts.append(
            f"Candidate domain: {candidate_domain}; required domain: "
            f"{required_domain_display}; domain assessment: "
            f"{domain_status_display}."
        )

        if (
            qualification_details.casefold() in UNKNOWN_VALUES
            or qualification_details.casefold() == "not verified"
        ):
            reason_parts.append(
                "Qualification information is unavailable and should be "
                "verified."
            )
        else:
            reason_parts.append(
                f"Available qualification details: {qualification_details}."
            )

        recommendation_reasons = {
            "Highly Recommended": (
                "The score is at least 75, direct coverage is at least 70%, "
                "and experience does not require review."
            ),
            "Recommended": (
                "The score is at least 60, direct coverage is at least 40%, "
                "and experience does not require review."
            ),
            "Needs Review": (
                "The score meets the 40-point review threshold, but the "
                "stronger recommendation criteria are not all met or "
                "experience needs recruiter review."
            ),
            "Not Recommended": (
                "The comparison score is below the 40-point review threshold; "
                "this is a ranking outcome, not an employment decision."
            ),
        }
        reason_parts.append(
            "Reason for this status: "
            + recommendation_reasons[recommendation]
        )

        candidate["Recommendation_Reason"] = " ".join(reason_parts)

    # Sort by ranking score, highest first.
    ranked_candidates = sorted(
        candidates,
        key=lambda candidate: candidate["Ranking_Score"],
        reverse=True,
    )

    # Assign one consistent Rank field and remove the lowercase version.
    for rank_number, candidate in enumerate(
        ranked_candidates,
        start=1,
    ):
        candidate["Rank"] = rank_number
        candidate.pop("rank", None)

    return ranked_candidates
