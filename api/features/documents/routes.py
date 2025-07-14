from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
from .utils import (
    verify_document_generation, 
    verify_document_edit,
    save_document_to_django,
)
from .chains import chain_instance
from .prompts import (
   cover_letter_prompt,
    recommendation_letter_prompt,
    motivation_letter_prompt,
    edit_docs_section_prompt
)


import yaml


class GenerateDocumentRequest(BaseModel):
    resume_id: int
    document_type: str  # "cover_letter", "recommendation_letter", "motivation_letter"
    other_info: Dict = {}
    language: str = "en"


class EditDocumentSectionRequest(BaseModel):
    document_type: str  # "cover_letter", "recommendation_letter", "motivation_letter"
    section_data: Dict
    prompt: str


router = APIRouter()


@router.post("/generate")
async def generate_document(
    request: GenerateDocumentRequest,
    auth_data: dict = Depends(verify_document_generation),
):
    """
    Generate a document (cover letter, recommendation letter, or motivation letter).
    
    Args:
        request: The document generation request data
        
    Returns:
        dict: The generated document
    """
    
    try:
        # Step 1: Extract data from request (now coming from frontend cache)
        personal_info = request.other_info.get("personal_info", {})
        about_candidate = request.other_info.get("about_candidate", "")
        additional_context = request.other_info.get("additional_context", "")
        
        # Step 2: Select the appropriate prompt based on document type
        prompt_mapping = {
            "cover_letter": cover_letter_prompt,
            "recommendation_letter": recommendation_letter_prompt,
            "motivation_letter": motivation_letter_prompt,
        }
        
        
        selected_prompt = prompt_mapping.get(request.document_type)
        if not selected_prompt:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported document type: {request.document_type}"
            )
        
        # Step 3: Create prompt and call chain
        chain = chain_instance.build_chain(selected_prompt)
        result = await chain.ainvoke(
            {
                "personal_info": yaml.dump(personal_info),
                "about_candidate": about_candidate,
                "other_info": additional_context,  # Only the additional user input
                "language": request.language,
            }
        )

        # Step 4: Parse result
        document_data = yaml.safe_load(result)
        
        # Step 5: Save to Django via API call
        saved_document = await save_document_to_django(
            request.resume_id, 
            document_data,
            request.document_type,
            auth_data["authorization"]
        )

        if not saved_document:
            # If saving fails, return an error instead of success
            raise HTTPException(
                status_code=500, 
                detail="Document was generated but failed to save to database. Please check if Django server is running and the /api/documents/ endpoint exists."
            )

        return {
            "success": True,    
            "document_id": saved_document["document_id"],  # Django returns document_uuid
            "document": saved_document,
            "remaining_uses": auth_data["remaining_uses"] - 1,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@router.post("/edit_section")
async def edit_document_section(
    request: EditDocumentSectionRequest,
    auth_data: dict = Depends(verify_document_edit),
):
    """
    Edit a specific section of a document.
    
    Args:
        request: The document section edit request data
        
    Returns:
        dict: The updated section content
    """
    
    try:
        # Step 1: Create prompt and call chain
        chain = chain_instance.build_chain(edit_docs_section_prompt)
        result = await chain.ainvoke(
            {
                "document_type": request.document_type,
                "section_yaml": yaml.dump(request.section_data),
                "prompt": request.prompt,
            }
        )

        # Step 2: Parse result
        section_data = yaml.safe_load(result)

        return section_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit document section: {str(e)}")
