
import os
import hmac
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Header, UploadFile, File

app = FastAPI(title="Talent Pool Rediscovery API")

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_FILE = RESULTS_DIR / "candidate_matching_results.csv"

API_TOKEN = os.environ.get("TALENT_API_TOKEN")


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


@app.get("/")
def home():
    return {
        "message": "Talent Pool Rediscovery API is running"
    }


@app.post("/upload-results")
async def upload_results(
    file: UploadFile = File(...),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    verify_api_token(x_api_key)

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="CSV file must be smaller than 10 MB."
        )

    try:
        results = pd.read_csv(BytesIO(content)).fillna("")

        if results.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV contains no results."
            )

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        results.to_csv(RESULTS_FILE, index=False)

        return {
            "message": "Matching results uploaded successfully.",
            "total_results": len(results)
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not read the uploaded CSV file."
        )


@app.get("/results")
def get_latest_results(
    x_api_key: str = Header(..., alias="X-API-Key")
):
    verify_api_token(x_api_key)

    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Matching results not found. Upload results first."
        )

    try:
        results = pd.read_csv(RESULTS_FILE).fillna("")

        return {
            "total_results": len(results),
            "results": results.to_dict(orient="records"),
            "message": "Latest Python matching results retrieved successfully."
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not read the matching results."
        )
