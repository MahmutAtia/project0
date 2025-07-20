from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingHttpResponse
from pydantic import BaseModel
from .utils import verify_pdf_generation, generate_pdf_via_django
import io


class GeneratePDFRequest(BaseModel):
    resume_id: int
    template_theme: str = "default.html"
    chosen_theme: str = "theme-default"


router = APIRouter()


def file_iterator(file_handle, chunk_size=8192):
    """Helper function to iterate over a file-like object in chunks."""
    while True:
        chunk = file_handle.read(chunk_size)
        if not chunk:
            break
        yield chunk


@router.post("/generate")
async def generate_pdf(
    request: GeneratePDFRequest,
    auth_data: dict = Depends(verify_pdf_generation),
):
    """
    Generate a PDF from resume data.
    
    Args:
        request: The PDF generation request data
        
    Returns:
        StreamingHttpResponse: The generated PDF file
    """
    
    try:
        # Generate PDF via Django service
        pdf_data = await generate_pdf_via_django(
            request.resume_id,
            request.template_theme,
            request.chosen_theme,
            auth_data["authorization"]
        )

        if not pdf_data:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")

        # Create streaming response
        pdf_buffer = io.BytesIO(pdf_data)
        filename = f"resume_{request.resume_id}.pdf"

        response = StreamingHttpResponse(
            file_iterator(pdf_buffer),
            media_type="application/pdf",
        )
        response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
        response.headers["Content-Length"] = str(len(pdf_data))
        
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

router.post