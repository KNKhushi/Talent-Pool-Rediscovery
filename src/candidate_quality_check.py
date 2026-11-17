import pandas as pd

INPUT_FILE = "data/dummy_candidates_10.xlsx"
OUTPUT_FILE = "results/dummy_candidate_quality.csv"

candidates = pd.read_excel(INPUT_FILE)

results = []

for _, candidate in candidates.iterrows():

    profile_text = str(candidate["Profile_Text"]).strip()

    if not profile_text or profile_text.lower() == "nan":
        status = "⚠ Information not available"
    elif len(profile_text.split()) < 10:
        status = "⚠ Limited information"
    else:
        status = "Available"

    results.append({
        "Candidate_ID": candidate["Candidate_ID"],
        "Candidate_Name": candidate["Candidate_Name"],
        "Profile_Quality": status,
        "Profile_Text_Length": len(profile_text.split())
    })

result_df = pd.DataFrame(results)

result_df.to_csv(OUTPUT_FILE, index=False)

print("\n========== CANDIDATE PROFILE QUALITY ==========\n")
print(result_df.to_string(index=False))

print(f"\nSaved to: {OUTPUT_FILE}")
