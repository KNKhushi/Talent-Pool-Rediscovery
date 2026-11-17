
import re


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "is", "it", "of", "on", "or", "the", "to",
    "with", "we", "you", "our", "your", "they", "their",
    "looking", "seeking", "responsible", "responsibilities",
    "required", "preferred", "ability", "must", "should",
}

# Preserve useful phrases as complete units.
KNOWN_PHRASES = [
    "financial reporting",
    "financial records",
    "financial statements",
    "financial transactions",
    "account reconciliation",
    "data entry",
    "customer service",
    "project management",
    "software development",
    "machine learning",
    "natural language processing",
    "salesforce developer",
    "sentence transformers",
]


def normalize_text(text):
    """Normalize text without inventing requirements."""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(text, top_n=10):
    """
    Extract useful words and phrases from supplied text.
    Does not add skills that are absent from the source text.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    normalized_text = normalize_text(text)
    keywords = []
    seen = set()

    # Add meaningful phrases that actually occur in the text.
    for phrase in KNOWN_PHRASES:
        if re.search(
            r"(?<![a-z0-9+#])"
            + re.escape(phrase)
            + r"(?![a-z0-9+#])",
            normalized_text,
        ):
            if phrase not in seen:
                keywords.append(phrase)
                seen.add(phrase)

    # Extract remaining useful individual words.
    words = normalized_text.split()

    for word in words:
        word = word.strip("-. ")

        if not word or word in STOP_WORDS:
            continue

        if len(word) < 2 or word in seen:
            continue

        keywords.append(word)
        seen.add(word)

    return keywords[:max(0, top_n)]


if __name__ == "__main__":
    sample = (
        "Accountant maintaining financial records, "
        "financial reporting, bookkeeping, Excel and data entry."
    )

    print("Test keywords:", extract_keywords(sample))
