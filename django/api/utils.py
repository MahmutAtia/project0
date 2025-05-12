import time
import logging

# handle files import 
from PyPDF2 import PdfReader
from docx import Document
import io


import re
import json
from django.conf import settings
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from collections import OrderedDict
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
    
def generate_html_from_yaml(json_data, template_name='html_bloks_template.html'):
    """
    Generates HTML from YAML data using a Jinja template.

    Args:
        yaml_data (dict): The YAML data as a dictionary.
        template_name (str, optional): The name of the Jinja template file.
            Defaults to 'utils.html.jinja'.

    Returns:
        str: The generated HTML as a string.  Returns None on error.
    """
    try:

        env = Environment(
            loader=FileSystemLoader('./html_templates/'),
            autoescape=select_autoescape(['html', 'xml'])  # Auto-escape HTML
        )
        template = env.get_template(template_name)

        # 4. Render the Jinja template with the data
        html_output = template.render(data=json_data)  # Pass the entire data dictionary

        return html_output

    except Exception as e:
        print(f"Error generating HTML: {e}")
        return None
############################  parse custom format  ############################
import re
import json

def parse_custom_format(site_text):
        # Extract HTML, CSS, JS blocks
    html_match = re.search(r"===HTML===\s*(.*?)\s*===CSS===", site_text, re.DOTALL)
    css_match = re.search(r"===CSS===\s*(.*?)\s*===JS===", site_text, re.DOTALL)
    js_match = re.search(r"===JS===\s*(.*)", site_text, re.DOTALL)

    html = html_match.group(1) if html_match else ""
    css = css_match.group(1) if css_match else ""
    js = js_match.group(1) if js_match else ""

    # Extract <head> content
    head_match = re.search(r"<!--\s*BEGIN head\s*-->(.*?)<!--\s*END head\s*-->", html, re.DOTALL)
    head_content = head_match.group(1).strip() if head_match else ""

    # Extract global HTML + DESCRIPTION
    global_html_match = re.search(
        r"<!--\s*BEGIN global\s*-->\s*<!--\s*DESCRIPTION:\s*(.*?)\s*-->\s*(.*?)<!--\s*END global\s*-->",
        html, re.DOTALL
    )
    global_description = global_html_match.group(1).strip() if global_html_match else ""
    global_html = global_html_match.group(2).strip() if global_html_match else ""

    # Extract global CSS and JS
    global_css = re.search(r"/\*\s*BEGIN global\s*\*/(.*?)/\*\s*END global\s*\*/", css, re.DOTALL)
    global_js = re.search(r"//\s*BEGIN global\s*(.*?)//\s*END global", js, re.DOTALL)

    result = {
        "head": head_content,
        "global": {
            "name": "global",
            "html": global_html,
            "css": global_css.group(1).strip() if global_css else "",
            "js": global_js.group(1).strip() if global_js else "",
            "feedback": global_description
        },
        "code_bloks": []
    }

    # Extract all sections in HTML with ID and DESCRIPTION
    html_sections = re.findall(
        r"<!--\s*BEGIN SECTION:\s*([\w_]+)\s*-->\s*"
        r"<!--\s*DESCRIPTION:\s*(.*?)\s*-->\s*"
        r"(.*?)"
        r"<!--\s*END SECTION:\s*\1\s*-->",
        html, re.DOTALL
    )

    for name, description, html_content in html_sections:
        css_section = re.search(
            rf"/\*\s*BEGIN SECTION:\s*{re.escape(name)}\s*\*/(.*?)/\*\s*END SECTION:\s*{re.escape(name)}\s*\*/",
            css, re.DOTALL
        )
        js_section = re.search(
            rf"//\s*BEGIN SECTION:\s*{re.escape(name)}\s*(.*?)//\s*END SECTION:\s*{re.escape(name)}",
            js, re.DOTALL
        )

        block = {
            "name": name,
            "feedback": description.strip(),
            "html": html_content.strip(),
            "css": css_section.group(1).strip() if css_section else "",
            "js": js_section.group(1).strip() if js_section else ""
        }
        result["code_bloks"].append(block)

    return result
############################## Convert JSON to text ##############################
def format_data_to_ordered_text(data, current_key_context, order_map, indent_level=0):
    """
    Formats a Python dictionary or list into ordered plain text lines.
    - data: The dictionary or list to format.
    - current_key_context: A string key to look up the order in order_map.
                           For resume_data, this will be "resume".
                           For nested dicts, it will be the key of that dict (e.g., "personal_information").
    - order_map: The dictionary defining the order of keys.
    - indent_level: Current indentation level for pretty printing.
    """
    output_lines = []
    indent = "  " * indent_level
    
    # Get the list of ordered keys specifically for the current_key_context.
    # If current_key_context is not in order_map (e.g. "personal_information" is not a key in the simplified ORDER_MAP),
    # keys_in_defined_order will be an empty list.
    keys_in_defined_order = order_map.get(current_key_context, [])

    if isinstance(data, dict):
        processed_keys = set()

        # 1. Process keys that are in the defined order for the current_key_context
        if keys_in_defined_order: # This will only be true for the "resume" context with the simplified map
            for key in keys_in_defined_order:
                if key in data:
                    value = data[key]
                    if isinstance(value, dict):
                        output_lines.append(f"{indent}{key}:")
                        # The 'key' (e.g., "personal_information") becomes the new context.
                        # Since "personal_information" is not a key in ORDER_MAP, its fields will be unordered.
                        output_lines.extend(format_data_to_ordered_text(value, key, order_map, indent_level + 1))
                    elif isinstance(value, list):
                        output_lines.append(f"{indent}{key}:")
                        # The 'key' of the list (e.g., "experience") is the context for its items.
                        # Since "experience" is not a key in ORDER_MAP defining item structure,
                        # fields of dict items in this list will be unordered.
                        for i, item in enumerate(value):
                            # output_lines.append(f"{indent}  - Item {i+1}:") # Optional list item marker
                            if isinstance(item, dict):
                                output_lines.extend(format_data_to_ordered_text(item, key, order_map, indent_level + 1))
                            elif isinstance(item, list):
                                output_lines.append(f"{indent}  - Sub-list Item {i+1}:")
                                for sub_idx, sub_item in enumerate(item):
                                    output_lines.append(f"{indent}    - {sub_item}")
                            else:
                                output_lines.append(f"{indent}  - {item}")
                    else: # Simple value
                        output_lines.append(f"{indent}{key}: {value}")
                    processed_keys.add(key)

        # 2. Process remaining keys (i.e., all keys if no order defined for current_key_context,
        #    or keys not listed in keys_in_defined_order if an order was partially defined)
        for key in data: # Iterate through all keys in the current dictionary
            if key not in processed_keys: # If not already processed by the ordered section
                value = data[key]
                if isinstance(value, dict):
                    output_lines.append(f"{indent}{key}:")
                    # Pass 'key' as context. If 'key' isn't in ORDER_MAP, its children are unordered.
                    output_lines.extend(format_data_to_ordered_text(value, key, order_map, indent_level + 1))
                elif isinstance(value, list):
                    output_lines.append(f"{indent}{key}:")
                    for i, item in enumerate(value):
                        # output_lines.append(f"{indent}  - Item {i+1}:") # Optional
                        if isinstance(item, dict):
                            # Pass 'key' (list's key) as context for items.
                            output_lines.extend(format_data_to_ordered_text(item, key, order_map, indent_level + 1))
                        elif isinstance(item, list):
                            output_lines.append(f"{indent}  - Sub-list Item {i+1}:")
                            for sub_idx, sub_item in enumerate(item):
                                output_lines.append(f"{indent}    - {sub_item}")
                        else:
                            output_lines.append(f"{indent}  - {item}")
                else: # Simple value
                    output_lines.append(f"{indent}{key}: {value}")
                    
    elif isinstance(data, list): # If the data itself is a list (e.g. a list of strings, or list of dicts passed directly)
        # current_key_context would be the key that this list was associated with in its parent dict,
        # or a generic context if this list is the top-level data.
        for i, item in enumerate(data):
            # output_lines.append(f"{indent}- Item {i+1}:") # Optional
            if isinstance(item, dict):
                # Use current_key_context to check if there's an order defined for items of this list type.
                # With the simplified map, this usually means fields within 'item' will be unordered.
                output_lines.extend(format_data_to_ordered_text(item, current_key_context, order_map, indent_level + (0 if indent_level == 0 else 1)))
            elif isinstance(item, list):
                output_lines.append(f"{indent}- Sub-list Item {i+1}:")
                for sub_idx, sub_item in enumerate(item):
                    output_lines.append(f"{indent}  - {sub_item}")
            else:
                output_lines.append(f"{indent}- {item}")
    else: # Simple data type (string, number, boolean)
        output_lines.append(f"{indent}{data}")
        
    return output_lines

