
import os
import hmac
from io import BytesIO

import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Header, UploadFile, File


app = FastAPI(title="Talent Pool Rediscovery API")

API_TOKEN = os.environ.get("TALENT_API_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TABLE_NAME = "talent_pool_results"


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


def verify_supabase_config():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase configuration is missing."
        )


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }


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
    verify_supabase_config()

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
        results_df = pd.read_csv(BytesIO(content)).fillna("")

        if results_df.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV contains no results."
            )

        results = results_df.to_dict(orient="records")

        payload = {
            "total_results": len(results),
            "results": results
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    **supabase_headers(),
                    "Prefer": "return=minimal"
                },
                json=payload
            )

        if response.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail="Could not save results to Supabase."
            )

        return {
            "message": "Matching results saved successfully.",
            "total_results": len(results)
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not process the uploaded CSV."
        )


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
            raise HTTPException(
                status_code=502,
                detail="Could not retrieve results from Supabase."
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
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve matching results."
        )
