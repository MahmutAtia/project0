from modules.utils import create_auth_dependency
from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os

# Django service URL
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")

async def save_resume_to_django(user_id: int, data: dict, authorization: str):
    """Save resume via Django API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DJANGO_API_URL}/api/resumes/",
                headers={"Authorization": authorization},
                json={
                    "resume": data.get("resume", {}),  # The main resume JSON data
                    "title": data.get("title", "Generated Resume"),
                    "description": data.get("description", ""),
                    "about": data.get("about_candidate", ""),
                    "job_search_keywords": data.get("job_search_keywords", ""),
                    "icon": data.get("fontawesome_icon", ""),
                    # Django will automatically set: user, is_default, created_at, updated_at
                },
            )

            if response.status_code == 201:
                return response.json()
            else:
                return None

        except httpx.RequestError:
            return None

# Create specific dependencies for different features
verify_resume_generation = create_auth_dependency("resume_generation")
verify_resume_section_edit = create_auth_dependency("resume_section_edit")
verify_pdf_generation = create_auth_dependency("pdf_generation")
