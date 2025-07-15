from modules.utils import create_auth_dependency
from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os

# Django service URL
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")



# Create specific dependencies for different features
verify_website_generation = create_auth_dependency("website_generation")
verify_website_edit = create_auth_dependency("resume_section_edit")
