
import os
import hmac
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Header


# Initialize FastAPI
app = FastAPI(title="Talent Pool Rediscovery API")


# Project directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Python matching pipeline output CSV
RESULTS_FILE = (
    PROJECT_ROOT / "results" / "candidate_matching_results.csv"
)

# API authentication token
API_TOKEN = os.environ.get("TALENT_API_TOKEN")


# Verify Salesforce API key
def verify_api_token(x_api_key):
    if not API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured."
        )

    if not hmac.compare_digest(x_api_key, API_TOKEN):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Talent Pool Rediscovery API is running"
    }


# Retrieve latest Python-generated matching results
@app.get("/results")
def get_latest_results(
    x_api_key: str = Header(..., alias="X-API-Key")
):
    verify_api_token(x_api_key)

    # Check whether Python has generated the CSV
    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Matching results not found. "
                "Run the Python matching pipeline first."
            )
        )

    try:
        # Read the latest matching results
        results = pd.read_csv(RESULTS_FILE).fillna("")

        # Return results to Salesforce
        return {
            "total_results": len(results),
            "results": results.to_dict(orient="records"),
            "message": (
                "Latest Python matching results "
                "retrieved successfully."
            )
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
