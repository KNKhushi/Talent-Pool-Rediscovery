
import re


RELATED_TERMS = {
    "executive assistant": [
        "administrative assistant",
        "administrative professional",
        "personal assistant",
        "executive support",
    ],
    "calendar management": [
        "executive schedules",
        "scheduling",
        "calendar coordination",
        "managing calendars",
    ],
    "meeting coordination": [
        "meetings",
        "meeting scheduling",
        "meeting management",
        "coordinating meetings",
    ],
    "travel arrangements": [
        "travel",
        "travel coordination",
        "business travel",
    ],
    "document management": [
        "documentation",
        "document coordination",
    ],
    "accounting": [
        "accountant",
        "accounting and finance",
        "financial accounting",
    ],
    "bookkeeping": [
        "maintaining financial records",
        "financial record keeping",
    ],
    "financial reporting": [
        "financial reports",
        "financial statements",
        "report preparation",
    ],
    "data entry": [
        "entering data",
        "data input",
        "recording transactions",
    ],
    "excel": [
        "microsoft excel",
        "spreadsheet",
        "spreadsheets",
    ],
    "microsoft excel": [
        "excel",
    ],
    "account reconciliation": [
        "bank reconciliation",
        "reconciling accounts",
    ],
}

RELATED_SKILL_EVIDENCE = {
    "sales": {
        "customer service",
        "customer support",
        "sales support",
    },
    "lead generation": {
        "cold calling",
        "outreach",
        "prospecting",
    },
    "customer relationship management": {
        "account management",
        "client relations",
        "customer service",
        "customer support",
    },
    "negotiation": {
        "contract management",
        "vendor management",
    },
}


def clean_keywords(keywords):
    """Normalize keyword values and remove duplicates."""
    if not keywords:
        return []

    if isinstance(keywords, str):
        keywords = re.split(r"[,;|\n]+", keywords)

    cleaned = []
    ignored_values = {
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

    for keyword in keywords:
        if not keyword:
            continue

        value = re.sub(
            r"\s+",
            " ",
            str(keyword)
        ).strip().lower()

        if value not in ignored_values and value not in cleaned:
            cleaned.append(value)

    return cleaned


def requirement_matches(requirement, candidate_text):
    """Check for direct or recognized related-term evidence."""
    requirement = requirement.lower().strip()

    if not requirement:
        return False

    terms = [requirement] + RELATED_TERMS.get(
        requirement,
        []
    )

    for term in terms:
        pattern = (
            r"(?<!\w)"
            + re.escape(term.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, candidate_text):
            return True

    return False


def extract_evidence_sentences(profile_text, matched_keywords):
    """
    Find supporting text from available candidate fields.

    These may be extracted profile fields rather than
    sentences from the candidate's original CV.
    """
    if not isinstance(profile_text, str):
        return []

    text = re.sub(r"\s+", " ", profile_text).strip()

    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    evidence = []

    for sentence in sentences:
        sentence_lower = sentence.lower()

        for keyword in matched_keywords:
            terms = [
                keyword.lower(),
                *RELATED_TERMS.get(keyword.lower(), [])
            ]

            if any(
                re.search(
                    r"(?<!\w)" + re.escape(term) + r"(?!\w)",
                    sentence_lower
                )
                for term in terms
            ):
                evidence.append(sentence.strip())
                break

    return list(dict.fromkeys(evidence))


def find_related_skill_evidence(requirement, candidate_items):
    """Return indirect evidence without treating it as a direct match."""
    related_terms = RELATED_SKILL_EVIDENCE.get(requirement, set())
    return [
        item
        for item in candidate_items
        if any(
            re.search(
                r"(?<!\w)" + re.escape(term) + r"(?!\w)",
                item,
            )
            for term in related_terms
        )
    ]


def check_missing_jd_requirements(jd_quality):
    """Return required fields missing from the job description."""
    if not isinstance(jd_quality, dict):
        return []

    missing = []

    for field, status in jd_quality.items():
        if (
            isinstance(status, str)
            and status.startswith("MISSING")
            and "Required field" in status
        ):
            missing.append(field.strip())

    return missing


def explain_candidate_match(
    profile_text,
    jd_keywords,
    candidate_keywords,
    jd_quality,
    required_skills=None,
    candidate_title=None,
    candidate_experience=None,
    candidate_qualifications=None,
):
    """
    Generate an explanation from each candidate's available data.

    Missing profile evidence is not proof that a candidate
    lacks a skill or qualification.
    """
    profile_text = str(profile_text or "")
    candidate_items = clean_keywords(candidate_keywords)
    candidate_title = str(candidate_title or "").strip()
    normalized_title = " ".join(candidate_title.casefold().split())

    # A title provides role context but is not evidence of a required skill.
    candidate_items = [
        item
        for item in candidate_items
        if " ".join(item.casefold().split()) != normalized_title
    ]

    evidence_text = profile_text.casefold()
    if normalized_title:
        evidence_text = re.sub(
            r"(?<!\w)" + re.escape(candidate_title) + r"(?!\w)",
            " ",
            evidence_text,
            flags=re.IGNORECASE,
        )
    candidate_text = evidence_text + " " + " ".join(candidate_items)

    requirements = clean_keywords(
        required_skills if required_skills else jd_keywords
    )

    matched = []
    unsupported = []
    related = {}

    for requirement in requirements:
        if requirement_matches(requirement, candidate_text):
            matched.append(requirement)
        else:
            unsupported.append(requirement)
            supporting_related = find_related_skill_evidence(
                requirement,
                candidate_items,
            )
            if supporting_related:
                related[requirement] = supporting_related

    missing = [
        requirement
        for requirement in unsupported
        if requirement not in related
    ]

    evidence = []
    for requirement in matched:
        supporting_items = [
            item
            for item in candidate_items
            if requirement_matches(requirement, item)
        ]
        if supporting_items:
            evidence.extend(supporting_items)
        else:
            evidence.extend(
                extract_evidence_sentences(
                    evidence_text,
                    [requirement],
                )
            )
    evidence = list(dict.fromkeys(evidence))

    coverage = len(matched) / len(requirements) if requirements else 0.0
    related_coverage = (
        len(related) / len(requirements)
        if requirements
        else 0.0
    )
    role = candidate_title
    if role.casefold() in {"not specified", "unknown", "needs review"}:
        role = ""

    experience = str(candidate_experience or "").strip()
    if experience.casefold() in {
        "nan", "none", "null", "n/a", "na", "not specified", "unknown"
    }:
        experience = ""

    qualifications = str(candidate_qualifications or "").strip()
    if qualifications.casefold() in {
        "nan", "none", "null", "n/a", "na", "not specified", "unknown"
    }:
        qualifications = ""

    if matched:
        explanation = "Listed skill evidence supports " + ", ".join(matched) + "."
    else:
        explanation = (
            "The available profile does not establish direct evidence "
            "for the listed JD requirements."
        )

    if role:
        explanation += (
            f" The listed role, {role}, is relevant context but does not "
            "by itself verify those skills."
        )
    if related:
        related_descriptions = [
            f"{requirement} (related evidence: {', '.join(items)})"
            for requirement, items in related.items()
        ]
        explanation += (
            " Potentially related evidence that needs verification: "
            + "; ".join(related_descriptions)
            + ". Related evidence is not counted as a direct skill match."
        )
    unmatched_profile_skills = [
        item
        for item in candidate_items
        if item not in evidence
        and not any(item in related_items for related_items in related.values())
    ]
    if unmatched_profile_skills:
        explanation += (
            " Other listed profile skills include "
            + ", ".join(unmatched_profile_skills[:4])
            + "; these do not directly establish another listed requirement."
        )
    if experience:
        explanation += f" Recorded experience: {experience} years."
    else:
        explanation += " Years of experience are unknown from the available data."

    # Missing evidence, not confirmed missing skills.
    if unsupported:
        missing_without_related = [
            requirement for requirement in unsupported
            if requirement in missing
        ]
        potential_gaps = (
            "Direct evidence is not listed for: "
            + ", ".join(unsupported)
            + "."
        )
        if related:
            potential_gaps += (
                " Related evidence requiring verification: "
                + "; ".join(
                    f"{requirement}: {', '.join(items)}"
                    for requirement, items in related.items()
                )
                + "."
            )
        if missing_without_related:
            potential_gaps += (
                " No related evidence was identified for: "
                + ", ".join(missing_without_related)
                + "."
            )
        potential_gaps += " Confirm requirements with the candidate."
    else:
        potential_gaps = (
            "No listed JD skill requirements remain unsupported in the "
            "available evidence; verify the details before shortlisting."
        )

    if not requirements:
        evidence_status = (
            "Insufficient information: no JD requirements to compare."
        )
    elif coverage >= 0.7:
        evidence_status = (
            f"Strong evidence - recruiter review: {len(matched)} of "
            f"{len(requirements)} listed requirements are supported."
        )
    elif coverage >= 0.4:
        evidence_status = (
            f"Partial evidence - recruiter review: {len(matched)} of "
            f"{len(requirements)} requirements have direct support."
        )
        if related:
            evidence_status += (
                f" Related evidence was found for {len(related)} other "
                "requirement(s), but needs verification."
            )
    else:
        evidence_status = (
            f"Insufficient evidence - lower priority: {len(matched)} of "
            f"{len(requirements)} requirements have direct support. "
            "This is not an automatic rejection."
        )
        if related:
            evidence_status += (
                f" Related evidence was found for {len(related)} "
                "requirement(s), but needs verification."
            )

    # JD warnings describe the JD, so they can be the same
    # for all candidates applying to the same job.
    jd_missing = check_missing_jd_requirements(jd_quality)

    if jd_missing:
        jd_warning = (
            "The JD is missing required fields: "
            + ", ".join(jd_missing)
            + ". Matching results may be affected."
        )
    else:
        jd_warning = "No missing required JD fields were detected."

    if not matched and related:
        recommendation = (
            "Review the related evidence for "
            + ", ".join(related)
            + " with the candidate; it does not yet verify those "
            "requirements directly."
        )
    elif not matched:
        recommendation = (
            "Keep as an unverified potential match; review detailed work "
            "history before considering a shortlist."
        )
    elif coverage >= 0.8:
        recommendation = (
            "Advance to recruiter review; validate the listed evidence "
            "and confirm experience before shortlisting."
        )
    elif coverage >= 0.4:
        recommendation = (
            "Review the supported skills and confirm the remaining "
            "requirements before shortlisting."
        )
    else:
        role_context = (
            f"The listed role ({role}) is context, not skill proof. "
            if role
            else ""
        )
        if related:
            role_context = (
                f"For the listed {role} role, "
                if role
                else "Given the candidate's listed skills, "
            )
            recommendation = (
                role_context
                + "verify "
                + "; ".join(
                    f"{requirement} based on {', '.join(items)}"
                    for requirement, items in related.items()
                )
                + " before shortlisting."
            )
        else:
            recommendation = (
                role_context
                + "Treat as a limited-evidence potential match; verify "
                "the unsupported requirements in the candidate's work history."
            )
    if not qualifications:
        recommendation += " Qualification details are unverified."

    return {
        "Matched_Keywords": ", ".join(matched),
        "Matched_Requirements": ", ".join(matched),
        "Requirement_Count": len(requirements),
        "Requirement_Coverage": round(coverage, 4),
        "Direct_Skill_Coverage": round(coverage, 4),
        "Related_Skill_Coverage": round(related_coverage, 4),
        "Related_Evidence": "; ".join(
            f"{requirement}: {', '.join(items)}"
            for requirement, items in related.items()
        ),
        "Potential_Gaps": potential_gaps,
        "Evidence_Sentences": " | ".join(evidence),
        "Evidence_Status": evidence_status,
        "Match_Explanation": explanation,
        "Missing_JD_Requirements": ", ".join(missing),
        "JD_Quality_Warning": jd_warning,
        "Recruiter_Recommendation": recommendation,
    }
