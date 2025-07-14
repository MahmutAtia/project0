from modules.utils import create_auth_dependency
from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os

# Django service URL
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")



async def save_document_to_django(resume_id: int, document_data: dict, document_type: str,
 authorization: str):
    """Save document data via Django API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DJANGO_API_URL}/api/resumes/document/create/",
                headers={"Authorization": authorization},
                json={
                    "resume_id": resume_id,
                    "json_content": document_data,
                    "document_type": document_type
                },
            )
            if response.status_code == 201:
                return response.json()
            else:
                return None
        except httpx.RequestError:
            return None

 


# Create specific dependencies for different features
verify_document_generation = create_auth_dependency("document_generation")
verify_document_edit = create_auth_dependency("resume_section_edit")
