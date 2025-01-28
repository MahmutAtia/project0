import time
import logging

# handle files import 
from PyPDF2 import PdfReader
from docx import Document
import io


def cleanup_old_sessions(request):
    """Remove session data older than 1 hour"""
    current_time = int(time.time())
    keys_to_delete = []
    
    for key in request.session.keys():
        if key.startswith('temp_resume_'):
            data = request.session.get(key)
            if data and (current_time - data['created_at']) > 3600:
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del request.session[key]




logger = logging.getLogger(__name__)

def extract_text_from_file(uploaded_file):
    try:
        content_type = uploaded_file.content_type
        text = ''

        if content_type == 'application/pdf':
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = '\n'.join([page.extract_text() for page in pdf_reader.pages])

        elif content_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ]:
            doc = Document(io.BytesIO(uploaded_file.read()))
            text = '\n'.join([para.text for para in doc.paragraphs])

        elif content_type == 'text/plain':
            text = uploaded_file.read().decode('utf-8')

        else:
            raise ValueError(f'Unsupported file type: {content_type}')

        return text

    except Exception as e:
        logger.error(f'Error extracting text from file: {e}')
        raise