from fastapi import APIRouter, HTTPException, Depends, Header ,BackgroundTasks, File, Form, UploadFile
from pydantic import BaseModel
from .utils import (
    save_resume_to_django,
    verify_resume_generation,
    verify_resume_section_edit,
    extract_text_from_file,
    generate_resume_and_update_django,
)
from .chains import chain_instance,ats_checker_chain, ats_checker_no_job_desc_chain
from .prompts import (
    create_resume_prompt,
    edit_resume_section_prompt
)
from modules.utils import safe_load_yaml_with_logging
import httpx
import yaml
from io import StringIO
import json
import os



class ResumeRequest(BaseModel):
    input_text: str
    language: str = ""
    job_description: str = ""
    instructions: str = ""


class ResumeSectionRequest(BaseModel):
    sectionTitle: str
    sectionData: dict
    prompt: str




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
        chain = chain_instance.build_chain(edit_resume_section_prompt)
        result = await chain.ainvoke(
            {
                "section_title": request.sectionTitle,
                "section_yaml": yaml.dump(request.sectionData),
                "prompt": request.prompt,
            }
        )

        # Parse result
        section_data = yaml.safe_load(result)

        return section_data
        
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
                "job_description": request.job_description or "the user did not provide a job description",
                "instructions": request.instructions or "the user did not provide any extra instructions",
            }
        )

        # Step 2: Parse the full result to extract metadata and the resume object
        parsed_data = safe_load_yaml_with_logging(result) 

        # The 'resume' part from the YAML
        resume_content_obj = parsed_data.get("resume", {})

        # Convert the ordered resume object back to a YAML string for storage, preserving key order
        string_stream = StringIO()
        yaml.dump(resume_content_obj, string_stream, sort_keys=False, default_flow_style=False)
        resume_yaml_string = string_stream.getvalue()

        # Prepare the payload for the Django API call
        django_payload = {
            "title": parsed_data.get("title", "Generated Resume"),
            "description": parsed_data.get("description", ""),
            "about_candidate": parsed_data.get("about_candidate", ""),
            "job_search_keywords": parsed_data.get("job_search_keywords", ""),
            "fontawesome_icon": parsed_data.get("fontawesome_icon", ""),
            "resume": resume_yaml_string # Send the raw, order-preserved YAML string
        }
        print(f"Prepared Django payload: {django_payload['resume'][:100]}...")  # Log first 100 chars of resume for debugging
        # Step 3: Save to Django via API call
        saved_resume = await save_resume_to_django(
            auth_data["user_id"], django_payload, auth_data["authorization"]
        )

        if not saved_resume:
            # If saving fails, still return the generated content (as a parsed object)
            return {
                "success": True,
                "content": parsed_data,
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





@router.post("/ats_checker_and_generate")
async def ats_checker_and_generate(
    background_tasks: BackgroundTasks,
    # make resume optional, if not provided, use form data
    resume: UploadFile = File(None),
    resume_text: str = Form(None),
    formData: str = Form(...),
):
    """
    New primary endpoint for the ATS checker.
    1. Receives file and form data directly from the frontend.
    2. Performs synchronous ATS check.
    3. Triggers asynchronous full resume generation.
    """
    # --- 1. Process Inputs ---
    # Pass the UploadFile object directly to the utility and await it
    if resume:
        text = await extract_text_from_file(resume)
    else:
        text = resume_text
    # The rest of your logic remains the same
    form_data = json.loads(formData)
    
    job_description = form_data.get("description", "")
    language = form_data.get("targetLanguage", "en")
    target_role = form_data.get("targetRole", "")
    generate_new_resume_flag = form_data.get("generate_new_resume", True)

    # --- 2. Synchronous ATS Check ---
    ats_chain = ats_checker_chain if job_description else ats_checker_no_job_desc_chain
    ats_result = await ats_chain.ainvoke({
        "input_text": text,
        "job_description": job_description,
        "target_role": target_role,
        "language": language,
        "user_input_role": target_role,
    })


    generation_task_id = None
    if generate_new_resume_flag:
        # --- 3. Create Task Record in Django ---
        create_task_url = f"{os.environ.get('DJANGO_API_URL', 'http://django:8000')}/api/create-task/"
        async with httpx.AsyncClient() as client:
            response = await client.post(create_task_url)
            response.raise_for_status()
            generation_task_id = response.json()["task_id"]
        
        print(f"Created task {generation_task_id} in Django.")

        # --- 4. Add Background Task ---
        background_tasks.add_task(
            generate_resume_and_update_django,
            generation_task_id,
            text,
            job_description,
            language,
            ats_result
        )
        print(f"Enqueued background generation for task {generation_task_id}.")

    # --- 5. Return Immediate Response ---
    return {
        "ats_result": ats_result,
        "generation_task_id": generation_task_id
    }

