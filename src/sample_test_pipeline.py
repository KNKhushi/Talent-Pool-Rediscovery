
from pathlib import Path
import json

import pandas as pd
from sentence_transformers import SentenceTransformer, util

from src.matching import match_candidate
from src.ranking import rank_candidates
from src.candidate_evidence import explain_candidate_match


JD_FILE = "results/sample_jd_test.json"
CANDIDATE_FILE = "data/dummy_candidates_10.xlsx"
OUTPUT_FILE = "results/sample_jd_test_results.csv"


def main():
    # Load the processed job description
    with open(JD_FILE, "r", encoding="utf-8") as file:
        jd = json.load(file)

    # Load the 10 dummy candidates
    candidates = pd.read_excel(CANDIDATE_FILE)

    # Load the embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    jd_text = str(jd.get("cleaned_job_text", "")).strip()
    if not jd_text:
        jd_text = str(jd.get("job_title", "")).strip()

    jd_keywords = jd.get("keywords", [])
    jd_quality = jd.get("quality_check", {})

    jd_embedding = model.encode(
        jd_text,
        convert_to_tensor=True,
    )

    results = []

    for _, candidate in candidates.iterrows():
        profile_text = str(candidate.get("Profile_Text", ""))
        candidate_keywords = [
            keyword.strip()
            for keyword in str(
                candidate.get("Extracted_Keywords", "")
            ).split(",")
            if keyword.strip()
        ]

        candidate_embedding = model.encode(
            profile_text,
            convert_to_tensor=True,
        )

        semantic_similarity = float(
            util.cos_sim(
                jd_embedding,
                candidate_embedding,
            ).item()
        )

        match_result = match_candidate(
            jd_keywords,
            candidate_keywords,
            semantic_similarity,
        )

        domain_match = (
            str(candidate.get("Domain", "")).strip().lower()
            == str(jd.get("domain", "")).strip().lower()
        )

        evidence_result = explain_candidate_match(
            profile_text=profile_text,
            jd_keywords=jd_keywords,
            candidate_keywords=candidate_keywords,
            jd_quality=jd_quality,
        )

        # Keep the evidence module's matched keywords and explanation.
        results.append({
            "Candidate_ID": candidate.get("Candidate_ID", ""),
            "Candidate_Name": candidate.get("Candidate_Name", ""),
            "Candidate_Domain": candidate.get("Domain", ""),
            "Domain_Match": domain_match,
            "Keyword_Score": match_result["keyword_score"],
            "Semantic_Similarity": match_result["semantic_similarity"],
            "Final_Score": match_result["final_score"],
            **evidence_result,
        })

    ranked_results = rank_candidates(results)
    result_df = pd.DataFrame(ranked_results)

    columns = [
        "rank",
        "Candidate_ID",
        "Candidate_Name",
        "Candidate_Domain",
        "Domain_Match",
        "Keyword_Score",
        "Semantic_Similarity",
        "Final_Score",
        "Matched_Keywords",
        "Evidence_Sentences",
        "Match_Explanation",
        "Missing_JD_Requirements",
        "JD_Quality_Warning",
    ]

    result_df = result_df[columns]

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)

    print("\n========== REAL JD + 10 DUMMY CANDIDATES ==========\n")
    print(result_df.to_string(index=False, col_space=12))
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
