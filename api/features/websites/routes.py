from fastapi import APIRouter, HTTPException, Depends 
from pydantic import BaseModel
from typing import Dict
from .utils import (
    verify_website_edit,
    verify_website_generation,
)
from .chains import chain_instance
from .prompts import (
    create_resume_website_bloks_prompt,
    edit_website_block_prompt

)

import yaml
import textwrap


router = APIRouter()


class EditWebsiteSectionRequest(BaseModel):
    block_name: str
    current_html: str
    current_css: str
    current_js: str
    prompt: str
    artifacts: list = []


@router.post("/edit_section")
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
        chain = chain_instance.build_chain(edit_website_block_prompt)
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
    
