from fastapi import APIRouter, HTTPException, Depends, Header ,BackgroundTasks
from pydantic import BaseModel
from typing import Dict
from .utils import (
    verify_website_edit,
    verify_website_generation,
    generate_website_and_update_django,
)
from .chains import chain_instance
from .prompts import (
    edit_website_block_prompt

)

import yaml
import textwrap
import os
import httpx


router = APIRouter()

class CreateResumeWebsiteRequest(BaseModel):
    resume : str
    preferences :str
    resumeId: int



class EditWebsiteSectionRequest(BaseModel):
    block_name: str
    current_html: str
    current_css: str
    current_js: str
    prompt: str
    artifacts: list = []


@router.post("/edit_section/")
async def edit_website_section(
    request: EditWebsiteSectionRequest,
    auth_data: dict = Depends(verify_website_edit),
):

    """
    Edits a specific section of a website.
    
    Args:
        request: The request data containing section details and prompt
        
    Returns:
        dict: The updated section data
    """
    try:
        # Create prompt and call chain
        chain = chain_instance.build_chain(edit_website_block_prompt, model="gemini-2.5-flash")
        result = await chain.ainvoke(
            {
               "current_name": request.block_name,
                "current_html": textwrap.indent(request.current_html, "  "),
                "current_css": textwrap.indent(request.current_css, "  "),
                "current_js": textwrap.indent(request.current_js, "  "),
                "prompt": request.prompt,
                "artifacts": request.artifacts,
            }

        )
        # Parse result
        section_data = yaml.safe_load(result)
        return section_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit section: {str(e)}"
        )
    





@router.post("/create_resume_website/")
async def create_resume_website(
    request: CreateResumeWebsiteRequest,
        background_tasks: BackgroundTasks,

    auth_data: dict = Depends(verify_website_generation),

):
    """
    Creates a resume website using the provided details.
    """
    generation_task_id = None
    create_task_url = f"{os.environ.get('DJANGO_API_URL', 'http://django:8000')}/api/create-task/"
    async with httpx.AsyncClient() as client:
        response = await client.post(create_task_url)
        response.raise_for_status()
        generation_task_id = response.json()["task_id"]

    # --- 2. Add Background Task ---
    background_tasks.add_task(
        generate_website_and_update_django,
        task_id=generation_task_id,
        resume_id=request.resumeId,
        preferences=request.preferences,
        user_id=auth_data["user_id"],
        resume_yaml=request.resume
    )
    print(f"Enqueued background website generation for task {generation_task_id}.")

    # --- 3. Return Immediate Response ---
    return {
        "message": "Website generation started.",
        "generation_task_id": generation_task_id,
    }

