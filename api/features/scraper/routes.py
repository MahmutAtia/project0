import asyncio
import functools # Import functools
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from jobspy import scrape_jobs # Assuming jobspy is installed and importable

# --- Pydantic Models for Request and Response ---
class JobSourcingParams(BaseModel):
    search_term: Optional[str] = Field(default=None, description="General search term for jobs.")
    location: Optional[str] = Field(default=None, description="Location to search for jobs.")
    country: Optional[str] = Field(default=None, description="Country for the job search (e.g., 'USA', 'UK', 'Egypt', 'Türkiye').")


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
router = APIRouter()

# --- Helper function to run blocking scrape_jobs in a thread ---
async def run_scrape_jobs_async(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Runs the synchronous scrape_jobs function in a separate thread
    to avoid blocking the asyncio event loop.
    """
    loop = asyncio.get_event_loop()
    try:
        # Use functools.partial to pass keyword arguments to scrape_jobs
        func_with_kwargs = functools.partial(scrape_jobs, **params)
        df_jobs = await loop.run_in_executor(None, func_with_kwargs)

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
    scraping_params = {
        "site_name": ["google","indeed", "linkedin"], #"zip_recruiter"], # Default sites
        "search_term": frontend_params.search_term,
        "location": frontend_params.location,
        "results_wanted": 20, # Default results
        "hours_old": 72, # Default hours_old (1 week)
        "country_indeed": frontend_params.country if frontend_params.country else "USA", # Default for Indeed if country not specified
        "google_search_term": f"{frontend_params.search_term} jobs near {frontend_params.location} since few days" ,
        "country": frontend_params.country,
        "country_aware": True, # Default country_aware
        # Add any other parameters from JobSourcingParams that scrape_jobs accepts
    }
    # Filter out None values because scrape_jobs might not expect them for all args
    # or might have its own internal defaults for None.
    # It's generally safer to only pass arguments that have actual values.
    final_scraping_params = {k: v for k, v in scraping_params.items() if v is not None}

    scraped_data = await run_scrape_jobs_async(final_scraping_params)

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
            verbose  =True# suming verbose is a field in the job_dict
                
            )
        )
    
    if not processed_jobs and not scraped_data: # Check if scraped_data was also empty
        # You might want to return an empty list or a specific message
        # If no jobs are found, it's often better to return an empty list (HTTP 200)
        # than a 404, unless the query itself was invalid.
        # raise HTTPException(status_code=404, detail="No jobs found matching your criteria.")
        pass


    return processed_jobs

# Example of how to include this router in your main FastAPI app:
# from fastapi import FastAPI
# from api.features.scraper.routes import router as scraper_router # Adjust import path as needed
#
# app = FastAPI()
#
# app.include_router(scraper_router) # The prefix="/scraper" is already in the router
#
# # To run: uvicorn main:app --reload