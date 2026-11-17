
from typing import Iterable


# --------------------------------------------------
# RELATED TERMS
# --------------------------------------------------

RELATED_TERMS = {
    "executive assistant": {
        "administrative assistant",
        "personal assistant",
        "executive support",
    },
    "administrative assistant": {
        "executive assistant",
        "personal assistant",
        "administrative support",
    },
    "calendar management": {
        "scheduling",
        "calendar coordination",
    },
    "meeting coordination": {
        "meeting scheduling",
        "meeting management",
    },
    "travel arrangements": {
        "travel coordination",
        "business travel",
    },
    "document management": {
        "documentation",
        "document coordination",
    },
    "python": {
        "python programming",
        "python development",
    },
    "sql": {
        "structured query language",
        "sql queries",
    },
    "git": {
        "version control",
        "git version control",
    },
    "rest apis": {
        "rest api",
        "restful api",
        "restful apis",
        "rest api development",
        "api development",
    },
    "debugging": {
        "troubleshooting",
        "software debugging",
        "debugging code",
    },
    "javascript": {
        "javascript programming",
        "js",
    },
    "html": {
        "html5",
    },
    "css": {
        "css3",
    },
    "bookkeeping": {
        "financial record keeping",
        "accounting records",
    },
    "financial reporting": {
        "financial reports",
        "financial statements",
    },
    "excel": {
        "microsoft excel",
        "spreadsheet analysis",
    },
}


# --------------------------------------------------
# KEYWORD NORMALIZATION
# --------------------------------------------------

def normalize_keyword(keyword: str) -> str:
    """Normalize a keyword for consistent comparison."""

    normalized = " ".join(str(keyword).casefold().strip().split())
    if normalized == "microsoft excel":
        return "excel"
    return normalized


def normalize_keywords(keywords: Iterable[str]) -> set[str]:
    """Normalize keywords and remove empty values."""

    if keywords is None:
        return set()

    if isinstance(keywords, str):
        keywords = [keywords]

    return {
        normalize_keyword(keyword)
        for keyword in keywords
        if keyword is not None and normalize_keyword(keyword)
    }


# --------------------------------------------------
# KEYWORD MATCHING
# --------------------------------------------------

def calculate_keyword_score(
    jd_keywords: Iterable[str],
    candidate_keywords: Iterable[str],
) -> tuple[float, list[str]]:
    """Score job requirements against candidate evidence."""

    jd_set = normalize_keywords(jd_keywords)
    candidate_set = normalize_keywords(candidate_keywords)

    if not jd_set:
        return 0.0, []

    total_score = 0.0
    matched_keywords = []

    for jd_keyword in sorted(jd_set):
        related_terms = normalize_keywords(
            RELATED_TERMS.get(jd_keyword, set())
        )

        if jd_keyword in candidate_set:
            total_score += 1.0
            matched_keywords.append(jd_keyword)

        elif candidate_set.intersection(related_terms):
            total_score += 0.5
            matched_keywords.append(
                f"{jd_keyword} (related term)"
            )

    return round(total_score / len(jd_set), 4), matched_keywords


def match_candidate(
    jd_keywords: Iterable[str],
    candidate_keywords: Iterable[str],
    semantic_similarity: float = 0.0,
) -> dict[str, float | list[str]]:
    """Match JD keywords against candidate skills and return scores."""

    keyword_score, matched_keywords = calculate_keyword_score(
        jd_keywords,
        candidate_keywords,
    )
    semantic_score = max(
        0.0,
        min(float(semantic_similarity), 1.0),
    )
    final_score = 0.70 * keyword_score + 0.30 * semantic_score

    return {
        "matched_keywords": matched_keywords,
        "keyword_score": keyword_score,
        "semantic_similarity": round(semantic_score, 4),
        "final_score": round(final_score, 4),
    }