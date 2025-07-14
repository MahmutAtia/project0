from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from .utils import (
    save_resume_to_django,
    verify_resume_generation,
    verify_resume_section_edit
)
from .chains import chain_instance
from .prompts import (
    create_resume_prompt,
    edit_section_prompt,
    generate_from_job_desc_prompt,
)
import yaml


class ResumeRequest(BaseModel):
    input_text: str
    language: str = ""
    job_description: str = ""
    instructions: str = ""


class ResumeSectionRequest(BaseModel):
    section_title: str
    section_yaml: str
    prompt: str


class GenerateFromInputRequest(BaseModel):
    input_text: str
    language: str = "en"
    job_description: str = ""
    instructions: str = ""


class GenerateFromJobDescRequest(BaseModel):
    job_description: str
    target_language: str = "en"
    document_preferences: dict = {}


router = APIRouter()


@router.post("/edit_section")
async def edit_section(
    request: ResumeSectionRequest,
    auth_data: dict = Depends(verify_resume_section_edit),
):
    """
    Edits a specific section of a resume.
    """
    try:
        # Create prompt and call chain
        chain = chain_instance.build_chain(edit_section_prompt)
        result = await chain.ainvoke(
            {
                "section_title": request.section_title,
                "section_yaml": request.section_yaml,
                "prompt": request.prompt,
            }
        )

        # Parse result
        section_data = yaml.safe_load(result)

        return {
            "success": True,
            "section": section_data,
            "remaining_uses": auth_data["remaining_uses"] - 1,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to edit section: {str(e)}"
        )


@router.post("/create_resume")
async def create_resume(
    request: ResumeRequest,
    auth_data: dict = Depends(verify_resume_generation),
):
    """
    Create a structured YAML file from a resume yaml.

    Args:
        request: The resume request data containing input_text, language, etc.

    Returns:
        dict: The structured YAML output.
    """

    try:
        # Step 1: Create prompt and call chain (FastAPI handles this well)
        chain = chain_instance.build_chain(create_resume_prompt)
        result = await chain.ainvoke(
            {
                "input_text": request.input_text,
                "language": request.language,
                "job_description": request.job_description,
                "instructions": request.instructions,
            }
        )

        # Step 2: Parse result
        resume_data = yaml.safe_load(result)

        # Step 3: Save to Django via API call
        saved_resume = await save_resume_to_django(
            auth_data["user_id"], resume_data, auth_data["authorization"]
        )

        if not saved_resume:
            # If saving fails, still return the generated content
            return {
                "success": True,
                "content": resume_data,
                "warning": "Resume generated but not saved to database",
            }

        return {
            "success": True,
            "resume_id": saved_resume["id"],
            "resume": saved_resume,
            "remaining_uses": auth_data["remaining_uses"] - 1,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


