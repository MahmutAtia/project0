import time
import logging

# handle files import 
from PyPDF2 import PdfReader
from docx import Document
import io


import json
from django.conf import settings
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
# from weasyprint.fonts import FontConfiguration # Optional - Not used, so removed



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
    
    
def generate_pdf_from_resume_data(resume_data, template_theme='resume_template_2.html', chosen_theme='theme-default'):
    """
    Generates a PDF from resume data.

    Args:
        resume_data (dict): The resume data as a dictionary.
        template_theme (str, optional): The name of the HTML template file.
            Defaults to 'resume_template_2.html'.
        chosen_theme (str, optional): The name of the CSS theme to apply.
            Defaults to 'theme-default'.

    Returns:
        bytes: The PDF file content as bytes. Returns None on error.
    """
    try:
        env = Environment(
            loader=FileSystemLoader('./html_templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template_theme)
        # Pass theme_class to the template
        html_out = template.render(theme_class=chosen_theme, **resume_data)
        html_obj = HTML(string=html_out, base_url='.') # added base_url
        pdf_file = html_obj.write_pdf()
        
        # Save the PDF to a file (optional)
        # pdf_file_path = f"resume.pdf"
        # with open(pdf_file_path, 'wb') as f:
        #     f.write(pdf_file)
        
        
        return pdf_file
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None