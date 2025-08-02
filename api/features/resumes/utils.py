from modules.utils import create_auth_dependency
from fastapi import HTTPException, Header, UploadFile
from PyPDF2 import PdfReader
from docx import Document
from typing import Optional
import httpx
from .chains import ats_create_resume_chain, ats_job_desc_resume_chain
import os
import io
import yaml




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

# This is the background function
async def generate_resume_and_update_django(task_id: str, resume_text: str, job_desc: str, language: str,ats_result:str):
    update_url = f"{DJANGO_API_URL}/api/update-task/"
    generated_resume = None
    try:
        # 1. Run the slow AI generation chain
        if job_desc and job_desc.strip():
            generated_resume = await ats_job_desc_resume_chain.ainvoke({
                "input_text": resume_text,
                "job_description": job_desc,
                "language": language,
                "ats_result": ats_result,
            })
        else:
            generated_resume = await ats_create_resume_chain.ainvoke({
                "input_text": resume_text,
                "language": language,
                "ats_result": ats_result,
            })

        # Add a check to ensure the AI returned a valid string
        if not generated_resume or not isinstance(generated_resume, str):
            raise ValueError("AI chain failed to return a valid resume string.")

        generated_resume_json = yaml.safe_load(generated_resume.replace("```yaml", "").replace("```", ""))



        # 2. Update the task in Django with the result
        payload = {"task_id": task_id, "status": "SUCCESS", "result": generated_resume_json}
        async with httpx.AsyncClient() as client:
            await client.post(update_url, json=payload)

    except Exception as e:
        # 3. If anything fails, update the task with an error
        print(f"Error occurred while generating resume: {e}")
        error_payload = {"task_id": task_id, "status": "FAILURE", "error": str(e)}
        async with httpx.AsyncClient() as client:
            await client.post(update_url, json=error_payload)


# --- MODIFIED FUNCTION ---
async def extract_text_from_file(uploaded_file: UploadFile):
    """
    Asynchronously reads an UploadFile and extracts its text content.
    """
    try:
        content_type = uploaded_file.content_type
        # Read the file content asynchronously ONCE.
        file_content = await uploaded_file.read()
        text = ""

        if content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(file_content))
            text = "\n".join([page.extract_text() for page in pdf_reader.pages])

        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            doc = Document(io.BytesIO(file_content))
            text = "\n".join([para.text for para in doc.paragraphs])

        elif content_type == "text/plain":
            text = file_content.decode("utf-8")

        else:
            # It's good practice to seek back to the start in case of retry logic
            await uploaded_file.seek(0)
            raise ValueError(f"Unsupported file type: {content_type}")

        return text

    except Exception as e:
        print(f"Error extracting text from file: {e}")
        raise


# Create specific dependencies for different features
verify_resume_generation = create_auth_dependency("resume_generation")
verify_resume_section_edit = create_auth_dependency("resume_section_edit")
verify_pdf_generation = create_auth_dependency("pdf_generation")



