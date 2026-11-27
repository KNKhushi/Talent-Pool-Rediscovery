import os
import hmac
from pathlib import Path
from datetime import datetime

import pandas as pd

from fastapi import FastAPI, HTTPException, Header, UploadFile, File


app = FastAPI(title="Talent Pool Rediscovery API")

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

RESULTS_FILE = RESULTS_DIR / "candidate_matching_results.csv"
UPLOADED_FILE = RESULTS_DIR / "uploaded_matching_results.csv"

API_TOKEN = os.environ.get("TALENT_API_TOKEN")


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def verify_api_token(x_api_key: str):

    if not API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured."
        )

    if not x_api_key or not hmac.compare_digest(
        x_api_key, API_TOKEN
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Talent Pool Rediscovery API is running",
        "status": "online"
    }


# --------------------------------------------------
# UPLOAD MATCHING RESULTS
# --------------------------------------------------

@app.post("/upload-results")
async def upload_results(
    file: UploadFile = File(...),
    x_api_key: str = Header(..., alias="X-API-Key")
):

    verify_api_token(x_api_key)

    if not file.filename or not file.filename.lower().endswith(".csv"):
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

        df = pd.read_csv(
            pd.io.common.BytesIO(content)
        )

        df = df.fillna("")

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV contains no results."
            )

        RESULTS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        df.to_csv(
            UPLOADED_FILE,
            index=False
        )

        return {
            "message": "Matching results uploaded successfully.",
            "total_results": len(df)
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


# --------------------------------------------------
# GET LATEST RESULTS
# --------------------------------------------------

@app.get("/results")
async def get_latest_results(
    x_api_key: str = Header(..., alias="X-API-Key")
):

    verify_api_token(x_api_key)

    try:

        if UPLOADED_FILE.exists():
            file_path = UPLOADED_FILE

        elif RESULTS_FILE.exists():
            file_path = RESULTS_FILE

        else:
            raise HTTPException(
                status_code=404,
                detail="No matching results CSV file found."
            )

        df = pd.read_csv(file_path)

        df = df.fillna("")

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail="No matching results found."
            )

        results = df.to_dict(
            orient="records"
        )

        return {
            "total_results": len(results),
            "results": results,
            "uploaded_at": datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(),
            "message": "Matching results retrieved successfully."
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve results: {str(e)}"
        )