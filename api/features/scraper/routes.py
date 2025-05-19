import asyncio
from fastapi import APIRouter, HTTPException, Query # Query is not strictly needed for POST body but can be for GET
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from jobspy import scrape_jobs # Assuming jobspy is installed and importable

# --- Pydantic Models for Request and Response ---
class JobSourcingParams(BaseModel):
    search_term: Optional[str] = Field(default=None, description="General search term for jobs.")
    location: Optional[str] = Field(default=None, description="Location to search for jobs.")
    google_search_term: Optional[str] = Field(default=None, description="Specific search term for Google Jobs. Overrides search_term for Google if provided.")
    country: Optional[str] = Field(default=None, description="Country for the job search (e.g., 'USA', 'UK', 'Egypt', 'Türkiye').")

    # Backend-controlled or default parameters (not sent by frontend)
    site_name: List[str] = Field(default=["google"], description="List of job sites to scrape.", exclude=True) # Exclude from request schema
    results_wanted: int = Field(default=20, ge=1, le=100, description="Number of job results wanted.", exclude=True)
    hours_old: Optional[int] = Field(default=168, ge=1, description="Filter jobs posted within the last x hours (e.g., 24 for last day, 168 for last week).", exclude=True)
    country_indeed: Optional[str] = Field(default="USA", description="Country for Indeed searches.", exclude=True)
    country_aware: Optional[bool] = Field(default=True, description="Whether the scraper should be country-aware.", exclude=True)


class ScrapedJob(BaseModel):
    id: Optional[str] = None
    site: Optional[str] = None
    job_url: Optional[HttpUrl] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    # Add other fields you want to return
    # job_url_direct: Optional[HttpUrl] = None
    # date_posted: Optional[str] = None # Or use datetime if you parse it
    # job_type: Optional[str] = None

# --- APIRouter ---
router = APIRouter(
    prefix="/scraper",
    tags=["Job Scraper"],
    responses={404: {"description": "Not found"}},
)

# --- Helper function to run blocking scrape_jobs in a thread ---
async def run_scrape_jobs_async(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Runs the synchronous scrape_jobs function in a separate thread
    to avoid blocking the asyncio event loop.
    """
    loop = asyncio.get_event_loop()
    try:
        # jobspy returns a pandas DataFrame, convert to list of dicts
        df_jobs = await loop.run_in_executor(None, scrape_jobs, **params)
        if df_jobs is not None and not df_jobs.empty:
            return df_jobs.to_dict(orient='records')
        return []
    except Exception as e:
        # Log the exception e
        print(f"Error during job scraping: {e}") # Replace with proper logging
        raise HTTPException(status_code=500, detail=f"An error occurred while scraping jobs: {str(e)}")

# --- API Endpoint ---
@router.post("/scrape-jobs/", response_model=List[ScrapedJob])
async def get_and_scrape_jobs(
    frontend_params: JobSourcingParams # Renamed for clarity
):
    """
    Asynchronously scrapes job data from specified sites based on input parameters
    sent from the frontend (`search_term`, `location`, `google_search_term`, `country`).
    Other scraping parameters are set with backend defaults.

    Returns a list of jobs with selected fields:
    - **id**: Unique identifier for the job listing.
    - **site**: The job board site (e.g., 'google', 'linkedin').
    - **job_url**: URL to the job posting.
    - **title**: Job title.
    - **company**: Company name.
    - **location**: Job location.
    - **is_remote**: Boolean indicating if the job is remote.
    """
    # Use backend defaults for parameters not sent by frontend
    # The JobSourcingParams model now has these defaults
    scraping_params = {
        "site_name": frontend_params.site_name, # Default from model
        "search_term": frontend_params.search_term,
        "location": frontend_params.location,
        "results_wanted": frontend_params.results_wanted, # Default from model
        "hours_old": frontend_params.hours_old, # Default from model
        "country_indeed": frontend_params.country_indeed, # Default from model
        "google_search_term": frontend_params.google_search_term,
        "country": frontend_params.country,
        "country_aware": frontend_params.country_aware, # Default from model
        # Add any other parameters from JobSourcingParams that scrape_jobs accepts
    }
    # Filter out None values
    scraping_params = {k: v for k, v in scraping_params.items() if v is not None}

    scraped_data = await run_scrape_jobs_async(scraping_params)

    processed_jobs: List[ScrapedJob] = []
    for job_dict in scraped_data:
        # Ensure HttpUrl conversion if job_url is present and not None
        job_url_value = job_dict.get("job_url")

        processed_jobs.append(
            ScrapedJob(
                id=job_dict.get("id"),
                site=job_dict.get("site"),
                job_url=HttpUrl(job_url_value) if job_url_value else None,
                title=job_dict.get("title"),
                company=job_dict.get("company"),
                location=job_dict.get("location"),
                is_remote=job_dict.get("is_remote"),
            )
        )
    
    if not processed_jobs:
        # You might want to return an empty list or a specific message
        # raise HTTPException(status_code=404, detail="No jobs found matching your criteria.")
        pass

    return processed_jobs

# --- Example of how to include this router in your main FastAPI app ---
# In your main.py or app.py:
# from fastapi import FastAPI
# from api.features.scraper.routes import router as scraper_router
#
# app = FastAPI()
#
# app.include_router(scraper_router)
#
# # To run: uvicorn main:app --reload