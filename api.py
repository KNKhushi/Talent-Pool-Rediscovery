import os
import hmac
from io import BytesIO

import pandas as pd
import httpx

from fastapi import FastAPI, HTTPException, Header, UploadFile, File


app = FastAPI(title="Talent Pool Rediscovery API")


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

API_TOKEN = os.environ.get("TALENT_API_TOKEN")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TABLE_NAME = "talent_pool_results"


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
# SUPABASE CONFIGURATION
# --------------------------------------------------

def verify_supabase_config():

    if not SUPABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_URL is missing."
        )

    if not SUPABASE_URL.startswith("https://"):
        raise HTTPException(
            status_code=503,
            detail="Invalid SUPABASE_URL. It must start with https://"
        )

    if not SUPABASE_KEY:
        raise HTTPException(
            status_code=503,
            detail="SUPABASE_KEY is missing."
        )


def supabase_headers():

    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


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
# UPLOAD MATCHING RESULTS TO SUPABASE
# --------------------------------------------------

@app.post("/upload-results")
async def upload_results(
    file: UploadFile = File(...),
    x_api_key: str = Header(..., alias="X-API-Key")
):

    verify_api_token(x_api_key)
    verify_supabase_config()

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

        # Read CSV
        results_df = pd.read_csv(
            BytesIO(content)
        )

        results_df = results_df.fillna("")

        if results_df.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV contains no results."
            )

        # Convert CSV into JSON records
        results = results_df.to_dict(
            orient="records"
        )

        # Supabase database record
        database_record = {
            "total_results": len(results),
            "results": results
        }

        # Save to Supabase
        async with httpx.AsyncClient(timeout=60) as client:

            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    **supabase_headers(),
                    "Prefer": "return=minimal"
                },
                json=[database_record]
            )

        # Check Supabase response
        if response.status_code not in (200, 201, 204):

            print("SUPABASE INSERT FAILED")
            print("STATUS:", response.status_code)
            print("RESPONSE:", response.text)

            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Supabase could not save the results.",
                    "status_code": response.status_code,
                    "supabase_error": response.text
                }
            )

        return {
            "message": "Matching results uploaded successfully.",
            "total_results": len(results)
        }

    except HTTPException:
        raise

    except Exception as e:

        print("UPLOAD ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


# --------------------------------------------------
# GET LATEST RESULTS FROM SUPABASE
# --------------------------------------------------

@app.get("/results")
async def get_latest_results(
    x_api_key: str = Header(..., alias="X-API-Key")
):

    verify_api_token(x_api_key)
    verify_supabase_config()

    try:

        async with httpx.AsyncClient(timeout=60) as client:

            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers=supabase_headers(),
                params={
                    "select": "total_results,results,uploaded_at",
                    "order": "uploaded_at.desc",
                    "limit": "1"
                }
            )

        if response.status_code != 200:

            print("SUPABASE FETCH FAILED")
            print("STATUS:", response.status_code)
            print("RESPONSE:", response.text)

            raise HTTPException(
                status_code=502,
                detail=f"Supabase retrieval failed: {response.text}"
            )

        records = response.json()

        if not records:

            raise HTTPException(
                status_code=404,
                detail="No matching results have been uploaded yet."
            )

        latest = records[0]

        return {
            "total_results": latest["total_results"],
            "results": latest["results"],
            "uploaded_at": latest["uploaded_at"],
            "message": "Latest matching results retrieved successfully."
        }

    except HTTPException:
        raise

    except Exception as e:

        print("RETRIEVAL ERROR:", str(e))

        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve results: {str(e)}"
        )