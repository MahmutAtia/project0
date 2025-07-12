import time
import logging

# handle files import
from PyPDF2 import PdfReader
from docx import Document
from pdf2docx import Converter
import tempfile
import os
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
        if key.startswith("temp_resume_"):
            data = request.session.get(key)
            if data and (current_time - data["created_at"]) > 3600:
                keys_to_delete.append(key)

    for key in keys_to_delete:
        del request.session[key]


logger = logging.getLogger(__name__)


def extract_text_from_file(uploaded_file):
    try:
        content_type = uploaded_file.content_type
        text = ""

        if content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = "\n".join([page.extract_text() for page in pdf_reader.pages])

        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            doc = Document(io.BytesIO(uploaded_file.read()))
            text = "\n".join([para.text for para in doc.paragraphs])

        elif content_type == "text/plain":
            text = uploaded_file.read().decode("utf-8")

        else:
            raise ValueError(f"Unsupported file type: {content_type}")

        return text

    except Exception as e:
        logger.error(f"Error extracting text from file: {e}")
        raise


def generate_pdf_from_resume_data(
    resume_data, template_theme="resume_template_2.html", chosen_theme="theme-default", sections_sort=None, hidden_sections=None
):
    """
    Generates a PDF from resume data.

    Args:
        resume_data (dict): The resume data as a dictionary.
        template_theme (str, optional): The name of the HTML template file.
            Defaults to 'resume_template_2.html'.
        chosen_theme (str, optional): The name of the CSS theme to apply.
            Defaults to 'theme-default'.
        sections_sort (list, optional): List of section keys in the desired order.
            If None, uses default order from template.
        hidden_sections (list, optional): List of section keys to hide.
            If None, no sections are hidden.

    Returns:
        bytes: The PDF file content as bytes. Returns None on error.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "html_templates")

        print(f"Base directory: {base_dir}")
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        
        # Get template configuration
        template_config = get_template_config(template_theme)
        
        # Use universal template if supported, otherwise use original template
        if template_config.get('use_universal', False):
            template = env.get_template('universal_template.html')
            # Add template configuration to context
            template_context = {
                "theme_class": chosen_theme,
                "template_style": template_config['template_style'],
                "layout_type": template_config['layout_type'],
                **resume_data
            }
        else:
            template = env.get_template(template_theme)
            # Prepare template context with sorted sections
            template_context = {
                "theme_class": chosen_theme,
                **resume_data
            }
        
        # If sections_sort is provided, add it to the template context
        if sections_sort:
            template_context["sections_sort"] = sections_sort
            
        # If hidden_sections is provided, add it to the template context
        if hidden_sections:
            template_context["hidden_sections"] = hidden_sections
        
        html_out = template.render(**template_context)
        html_obj = HTML(string=html_out, base_url=base_dir)
        pdf_file = html_obj.write_pdf()

        return pdf_file
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None


def generate_html_from_yaml(json_data, template_name="html_bloks_template.html"):
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
            loader=FileSystemLoader("./html_templates/"),
            autoescape=select_autoescape(["html", "xml"]),  # Auto-escape HTML
        )
        template = env.get_template(template_name)

        # 4. Render the Jinja template with the data
        html_output = template.render(data=json_data)  # Pass the entire data dictionary

        return html_output

    except Exception as e:
        print(f"Error generating HTML: {e}")
        return None


############################  parse custom format  ############################


def parse_custom_format(site_text):
    # Extract HTML, CSS, JS blocks
    html_match = re.search(r"===HTML===\s*(.*?)\s*===CSS===", site_text, re.DOTALL)
    css_match = re.search(r"===CSS===\s*(.*?)\s*===JS===", site_text, re.DOTALL)
    js_match = re.search(r"===JS===\s*(.*)", site_text, re.DOTALL)

    html = html_match.group(1) if html_match else ""
    css = css_match.group(1) if css_match else ""
    js = js_match.group(1) if js_match else ""

    # Extract <head> content
    head_match = re.search(r"<head>(.*?)</head>", html, re.DOTALL)
    head_content = head_match.group(1).strip() if head_match else ""

    # Extract global HTML (DESCRIPTION optional)
    global_html_match = re.search(
        r"<!--\s*BEGIN global\s*-->\s*(?:<!--\s*DESCRIPTION:\s*(.*?)\s*-->\s*)?(.*?)<!--\s*END global\s*-->",
        html,
        re.DOTALL,
    )
    global_description = (
        global_html_match.group(1).strip()
        if global_html_match and global_html_match.group(1)
        else ""
    )
    global_html = global_html_match.group(2).strip() if global_html_match else ""

    # Extract global CSS and JS
    global_css = re.search(
        r"/\*\s*BEGIN global\s*\*/(.*?)/\*\s*END global\s*\*/", css, re.DOTALL
    )
    global_js = re.search(r"//\s*BEGIN global\s*(.*?)//\s*END global", js, re.DOTALL)

    result = {
        "head": head_content,
        "global": {
            "name": "global",
            "html": global_html,
            "css": global_css.group(1).strip() if global_css else "",
            "js": global_js.group(1).strip() if global_js else "",
            "feedback": global_description,
        },
        "code_bloks": [],
    }

    # Extract section blocks, DESCRIPTION optional
    section_pattern = re.compile(
        r"<!--\s*BEGIN SECTION:\s*([\w_]+)\s*-->\s*"
        r"(?:<!--\s*DESCRIPTION:\s*(.*?)\s*-->\s*)?"
        r"(.*?)"
        r"<!--\s*END SECTION:\s*\1\s*-->",
        re.DOTALL,
    )

    for match in section_pattern.finditer(html):
        name = match.group(1)
        description = match.group(2).strip() if match.group(2) else ""
        html_content = match.group(3).strip()

        css_section = re.search(
            rf"/\*\s*BEGIN SECTION:\s*{re.escape(name)}\s*\*/(.*?)/\*\s*END SECTION:\s*{re.escape(name)}\s*\*/",
            css,
            re.DOTALL,
        )
        js_section = re.search(
            rf"//\s*BEGIN SECTION:\s*{re.escape(name)}\s*(.*?)//\s*END SECTION:\s*{re.escape(name)}",
            js,
            re.DOTALL,
        )

        block = {
            "name": name,
            "feedback": description,
            "html": html_content,
            "css": css_section.group(1).strip() if css_section else "",
            "js": js_section.group(1).strip() if js_section else "",
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
        if (
            keys_in_defined_order
        ):  # This will only be true for the "resume" context with the simplified map
            for key in keys_in_defined_order:
                if key in data:
                    value = data[key]
                    if isinstance(value, dict):
                        output_lines.append(f"{indent}{key}:")
                        # The 'key' (e.g., "personal_information") becomes the new context.
                        # Since "personal_information" is not a key in ORDER_MAP, its fields will be unordered.
                        output_lines.extend(
                            format_data_to_ordered_text(
                                value, key, order_map, indent_level + 1
                            )
                        )
                    elif isinstance(value, list):
                        output_lines.append(f"{indent}{key}:")
                        # The 'key' of the list (e.g., "experience") is the context for its items.
                        # Since "experience" is not a key in ORDER_MAP defining item structure,
                        # fields of dict items in this list will be unordered.
                        for i, item in enumerate(value):
                            # output_lines.append(f"{indent}  - Item {i+1}:") # Optional list item marker
                            if isinstance(item, dict):
                                output_lines.extend(
                                    format_data_to_ordered_text(
                                        item, key, order_map, indent_level + 1
                                    )
                                )
                            elif isinstance(item, list):
                                output_lines.append(f"{indent}  - Sub-list Item {i+1}:")
                                for sub_idx, sub_item in enumerate(item):
                                    output_lines.append(f"{indent}    - {sub_item}")
                            else:
                                output_lines.append(f"{indent}  - {item}")
                    else:  # Simple value
                        output_lines.append(f"{indent}{key}: {value}")
                    processed_keys.add(key)

        # 2. Process remaining keys (i.e., all keys if no order defined for current_key_context,
        #    or keys not listed in keys_in_defined_order if an order was partially defined)
        for key in data:  # Iterate through all keys in the current dictionary
            if (
                key not in processed_keys
            ):  # If not already processed by the ordered section
                value = data[key]
                if isinstance(value, dict):
                    output_lines.append(f"{indent}{key}:")
                    # Pass 'key' as context. If 'key' isn't in ORDER_MAP, its children are unordered.
                    output_lines.extend(
                        format_data_to_ordered_text(
                            value, key, order_map, indent_level + 1
                        )
                    )
                elif isinstance(value, list):
                    output_lines.append(f"{indent}{key}:")
                    for i, item in enumerate(value):
                        # output_lines.append(f"{indent}  - Item {i+1}:") # Optional
                        if isinstance(item, dict):
                            # Pass 'key' (list's key) as context for items.
                            output_lines.extend(
                                format_data_to_ordered_text(
                                    item, key, order_map, indent_level + 1
                                )
                            )
                        elif isinstance(item, list):
                            output_lines.append(f"{indent}  - Sub-list Item {i+1}:")
                            for sub_idx, sub_item in enumerate(item):
                                output_lines.append(f"{indent}    - {sub_item}")
                        else:
                            output_lines.append(f"{indent}  - {item}")
                else:  # Simple value
                    output_lines.append(f"{indent}{key}: {value}")

    elif isinstance(
        data, list
    ):  # If the data itself is a list (e.g. a list of strings, or list of dicts passed directly)
        # current_key_context would be the key that this list was associated with in its parent dict,
        # or a generic context if this list is the top-level data.
        for i, item in enumerate(data):
            # output_lines.append(f"{indent}- Item {i+1}:") # Optional
            if isinstance(item, dict):
                # Use current_key_context to check if there's an order defined for items of this list type.
                # With the simplified map, this usually means fields within 'item' will be unordered.
                output_lines.extend(
                    format_data_to_ordered_text(
                        item,
                        current_key_context,
                        order_map,
                        indent_level + (0 if indent_level == 0 else 1),
                    )
                )
            elif isinstance(item, list):
                output_lines.append(f"{indent}- Sub-list Item {i+1}:")
                for sub_idx, sub_item in enumerate(item):
                    output_lines.append(f"{indent}  - {sub_item}")
            else:
                output_lines.append(f"{indent}- {item}")
    else:  # Simple data type (string, number, boolean)
        output_lines.append(f"{indent}{data}")

    return output_lines


def convert_pdf_to_docx(pdf_content, output_path=None):
    """
    Converts PDF content to DOCX format.

    Args:
        pdf_content (bytes): The PDF content as bytes
        output_path (str, optional): Path to save the output DOCX. If None, only the BytesIO object is returned.

    Returns:
        BytesIO: A BytesIO object containing the DOCX content
    """
    try:
        # Create temporary files for the conversion process
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_temp:
            pdf_temp.write(pdf_content)
            pdf_temp_path = pdf_temp.name

        docx_temp_path = pdf_temp_path.replace(".pdf", ".docx")

        # Convert PDF to DOCX
        cv = Converter(pdf_temp_path)
        cv.convert(docx_temp_path)
        cv.close()

        # Read the DOCX file into memory
        with open(docx_temp_path, "rb") as docx_file:
            docx_content = io.BytesIO(docx_file.read())

        # Optionally save the DOCX to the specified output path
        if output_path:
            with open(output_path, "wb") as f:
                f.write(docx_content.getvalue())

        # Clean up temporary files
        os.unlink(pdf_temp_path)
        os.unlink(docx_temp_path)

        docx_content.seek(0)
        return docx_content

    except Exception as e:
        print(f"Error converting PDF to DOCX: {e}")
        return None


def generate_docx_from_template(
    resume_data, template_theme="resume_template_2.html", chosen_theme="theme-default", sections_sort=None, hidden_sections=None
):
    """
    Generates a DOCX document from template data using WeasyPrint to PDF and then converting to DOCX.

    Args:
        resume_data (dict): The document data as a dictionary
        template_theme (str): The HTML template to use
        chosen_theme (str): CSS theme class name
        sections_sort (list, optional): List of section keys in the desired order
        hidden_sections (list, optional): List of section keys to hide

    Returns:
        BytesIO: The DOCX file content as BytesIO object. Returns None on error.
    """
    try:
        # First generate PDF using existing function
        pdf_content = generate_pdf_from_resume_data(
            resume_data, template_theme, chosen_theme, sections_sort, hidden_sections
        )

        if pdf_content:
            # Convert PDF to DOCX
            docx_content = convert_pdf_to_docx(pdf_content)
            return docx_content
        return None
    except Exception as e:
        print(f"Error generating DOCX: {e}")
        return None


def get_template_config(template_name):
    """
    Returns template configuration based on template name.
    
    Args:
        template_name (str): Name of the template file
        
    Returns:
        dict: Configuration dictionary with template_style and layout_type
    """
    template_configs = {
        'template1.html': {
            'template_style': 'europass',
            'layout_type': 'europass',
            'use_universal': True
        },
        'template2.html': {
            'template_style': 'modern',
            'layout_type': 'two_column',
            'use_universal': True
        },
        'default.html': {
            'template_style': 'default',
            'layout_type': 'single_column',
            'use_universal': True
        },
        'default_sorted.html': {
            'template_style': 'default',
            'layout_type': 'single_column',
            'use_universal': True
        }
    }
    
    return template_configs.get(template_name, {
        'template_style': 'default',
        'layout_type': 'single_column',
        'use_universal': False
    })
