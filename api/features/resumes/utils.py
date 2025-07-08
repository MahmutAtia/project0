from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os

# Django service URL
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")


async def verify_user_and_limits(authorization: Optional[str] = Header(None)):
    """Call Django service to verify user and check limits"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    async with httpx.AsyncClient() as client:
        try:
            # Call Django API to verify token and check limits
            response = await client.get(
                f"{DJANGO_API_URL}/accounts/verify-and-check-limits/",
                headers={"Authorization": authorization},
                params={"feature": "resume_generation"},
            )

            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid token")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Feature limit exceeded")
            elif response.status_code != 200:
                raise HTTPException(status_code=500, detail="Auth service error")

            return response.json()  # Returns user info and limits

        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Cannot reach auth service")


async def save_resume_to_django(user_id: int, resume_data: dict, authorization: str):
    """Save resume via Django API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DJANGO_API_URL}/api/resumes/",
                headers={"Authorization": authorization},
                json={
                    "resume": resume_data.get(
                        "resume", {}
                    ),  # The main resume JSON data
                    "title": resume_data.get("title", "Generated Resume"),
                    "description": resume_data.get("description", ""),
                    "about": resume_data.get("about", ""),
                    "job_search_keywords": resume_data.get("job_search_keywords", ""),
                    "icon": resume_data.get("fontawesome_icon", ""),
                    # Django will automatically set: user, is_default, created_at, updated_at
                },
            )

            if response.status_code == 201:
                return response.json()
            else:
                return None

        except httpx.RequestError:
            return None
