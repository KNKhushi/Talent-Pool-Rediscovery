import os
import hmac
import logging
from io import BytesIO

import pandas as pd
import httpx

from fastapi import FastAPI, HTTPException, Header, UploadFile, File


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app = FastAPI(
    title="Talent Pool Rediscovery API",
    description="API for Python-based candidate matching and Salesforce integration",
    version="2.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

API_TOKEN = os.environ.get("TALENT_API_TOKEN")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
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

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is missing."
        )

    if not hmac.compare_digest(x_api_key, API_TOKEN):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key."
        )


# --------------------------------------------------
# SUPABASE CONFIGURATION
# --------------------------------------------------

def verify_supabase_config():

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase configuration is missing."
        )

    if not SUPABASE_URL.startswith("https://"):
        raise HTTPException(
            status_code=503,
            detail="Invalid Supabase URL configuration."
        )


def supabase_headers():

    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


# --------------------------------------------------
# HOME ENDPOINT
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Talent Pool Rediscovery API is running",
        "status": "online"
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "Talent Pool Rediscovery API"
    }


# --------------------------------------------------
# UPLOAD MATCHING RESULTS
# --------------------------------------------------

@app.post("/upload-results")
async def upload_results(
    file: UploadFile = File(...),
    x_api_key: str = Header(..., alias="X-API-Key")
):

    # Authenticate request
    verify_api_token(x_api_key)

    # Verify Supabase configuration
    verify_supabase_config()

    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    # Read uploaded file
    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    # Maximum file size: 10 MB
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="CSV file must be smaller than 10 MB."
        )

    # --------------------------------------------------
    # PROCESS CSV
    # --------------------------------------------------

    try:

        results_df = pd.read_csv(
            BytesIO(content),
            encoding="utf-8-sig"
        )

        # Remove completely empty rows
        results_df = results_df.dropna(how="all")

        # Replace missing values
        results_df = results_df.fillna("")

        if results_df.empty:
            raise HTTPException(
                status_code=400,
                detail="The uploaded CSV contains no results."
            )

        if len(results_df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="The CSV does not contain valid columns."
            )

        # Convert DataFrame into JSON-compatible records
        results = results_df.to_json(
            orient="records",
            force_ascii=False
        )

        import json

        results = json.loads(results)

        total_results = len(results)

        logger.info(
            "CSV processed successfully. Total records: %s",
            total_results
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.exception("CSV processing failed")

        raise HTTPException(
            status_code=400,
            detail=f"Could not process CSV file: {str(e)}"
        )


    # --------------------------------------------------
    # SAVE RESULTS TO SUPABASE
    # --------------------------------------------------

    payload = [
        {
            "total_results": total_results,
            "results": results
        }
    ]

    try:

        async with httpx.AsyncClient(timeout=60) as client:

            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    **supabase_headers(),
                    "Prefer": "return=minimal"
                },
                json=payload
            )

        # Supabase insert success
        if response.status_code in (200, 201, 204):

            logger.info(
                "Successfully saved %s records to Supabase.",
                total_results
            )

            return {
                "status": "success",
                "message": "Matching results saved successfully.",
                "total_results": total_results
            }

        # Log the actual Supabase error
        logger.error(
            "Supabase insert failed. Status: %s, Response: %s",
            response.status_code,
            response.text
        )

        raise HTTPException(
            status_code=502,
            detail="Supabase could not save matching results. Check Render logs."
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.exception("Supabase connection failed")

        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to Supabase: {str(e)}"
        )


# --------------------------------------------------
# GET LATEST MATCHING RESULTS
# --------------------------------------------------

@app.get("/results")
async def get_latest_results(
    x_api_key: str = Header(..., alias="X-API-Key")
):

    # Authenticate request
    verify_api_token(x_api_key)

    # Verify Supabase configuration
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

        # Check Supabase response
        if response.status_code != 200:

            logger.error(
                "Supabase retrieval failed. Status: %s, Response: %s",
                response.status_code,
                response.text
            )

            raise HTTPException(
                status_code=502,
                detail="Could not retrieve results from Supabase."
            )

        records = response.json()

        # No uploaded results available
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

        logger.exception("Failed to retrieve results")

        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve matching results: {str(e)}"
        )