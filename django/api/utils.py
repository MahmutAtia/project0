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



def parse_custom_format_to_json(input_string):
    """
    Parses a custom string format (similar to YAML but with flexible
    multi-line indentation) into a Python dictionary using regular expressions.

    Includes print statements for debugging the input string content
    and initial regex matches.

    Args:
        input_string: The string containing the custom format data.

    Returns:
        A Python dictionary representing the parsed data, or None if parsing fails.
    """
    # --- Debugging Prints ---
    print(f"--- Debugging Input String ---")
    print(f"Received input string (repr): {repr(input_string)}")
    print(f"Received input string:\n---\n{input_string}\n---")
    print(f"----------------------------")
    # ------------------------

    data = {}

    # Define common whitespace including non-breaking space
    WHITESPACE = r'[\s\u00a0]'

    # Regex to capture the global section
    # Using (?s) flag for '.' to match newlines
    # Updated to handle non-breaking spaces and more robustly capture multi-line fields
    # Assumes multi-line content starts on the line after the '|'
    # Adjusted to be more flexible with whitespace around keys
    global_regex = re.compile(rf'(?s)global:{WHITESPACE}*\n' # Match 'global:' followed by optional whitespace and a newline
                              rf'{WHITESPACE}*name:{WHITESPACE}*"(?P<global_name>.*?)"{WHITESPACE}*\n' # Match 'name:', optional whitespace, quoted value, optional whitespace, newline
                              rf'{WHITESPACE}*feedback:{WHITESPACE}*"(?P<global_feedback>.*?)"{WHITESPACE}*\n' # Match 'feedback:', optional whitespace, quoted value, optional whitespace, newline
                              rf'{WHITESPACE}*js:{WHITESPACE}*\|{WHITESPACE}*\n(?P<global_js>.*?)(?={WHITESPACE}*css:)' # Match 'js: |', newline, capture content until 'css:'
                              rf'{WHITESPACE}*css:{WHITESPACE}*\|{WHITESPACE}*\n(?P<global_css>.*?)(?={WHITESPACE}*html:)' # Match 'css: |', newline, capture content until 'html:'
                              rf'{WHITESPACE}*html:{WHITESPACE}*\|{WHITESPACE}*\n(?P<global_html>.*?)(?={WHITESPACE}*code_bloks:|\Z)') # Match 'html: |', newline, capture content until 'code_bloks:' or end of string (\Z)

    # --- Debugging Print for Global Match ---
    print(f"Attempting to find global section...")
    # ----------------------------------------

    global_match = global_regex.search(input_string)

    if global_match:
        print("Debug: Global section regex matched successfully.")
        data['global'] = global_match.groupdict()
        # Clean up leading/trailing whitespace from multi-line fields
        for key in ['global_js', 'global_css', 'global_html']:
             if data['global'][key] is not None:
                 data['global'][key] = data['global'][key].strip()
        # Clean up the feedback string
        if data['global']['global_feedback'] is not None:
             data['global']['global_feedback'] = data['global']['global_feedback'].strip()
    else:
        print("Warning: Global section not found. Check input string format.")
        data['global'] = {} # Initialize empty if not found

    # Regex to capture the code_bloks section content
    # Updated to handle non-breaking spaces and potential whitespace/newlines before '['
    # We need to find the start of code_bloks and the content within the brackets
    code_bloks_section_start_match = re.search(rf'(?s)code_bloks:{WHITESPACE}*\[', input_string)

    data['code_bloks'] = []

    if code_bloks_section_start_match:
        print("Debug: Found 'code_bloks: [' marker.")
        # Define the string to search for the content within brackets
        # Start searching from the position immediately after the '['
        search_string_for_blocks = input_string[code_bloks_section_start_match.end():]

        # --- Debugging Print for Code Blocks Search String ---
        print(f"Debug: Searching for code blocks content in string slice:\n---\n{search_string_for_blocks}\n---")
        # ------------------------------------------------------

        # Regex to capture the content between the first '[' after 'code_bloks:' and the final ']'
        # This regex is applied to the slice starting after '['
        code_bloks_content_regex = re.compile(rf'(?s)(.*?)]')
        code_bloks_content_match = code_bloks_content_regex.search(search_string_for_blocks)

        # --- Debugging Print for Code Blocks Content Match Result ---
        print(f"Debug: Result of regex search for code_bloks content: {code_bloks_content_match}")
        # ----------------------------------------------------------


        if code_bloks_content_match:
            code_bloks_content = code_bloks_content_match.group(1)
            print(f"Debug: Captured code_bloks content:\n---\n{code_bloks_content}\n---")

            # Regex to capture individual code blocks within the section
            # Using (?s) flag for '.' to match newlines
            # Updated to handle non-breaking spaces and more robustly capture multi-line fields
            # Assumes multi-line content starts on the line after the '|'
            # Adjusted to be more flexible with whitespace around keys and handle the end of the string
            block_regex = re.compile(rf'(?s){WHITESPACE}*-\{WHITESPACE}*\n'  # Match optional whitespace, '-', optional whitespace and a newline (start of a block item)
                                      rf'{WHITESPACE}*name:{WHITESPACE}*"(?P<block_name>.*?)"{WHITESPACE}*\n'  # Match 'name:', optional whitespace, quoted value, optional whitespace, newline
                                      rf'{WHITESPACE}*feedback:{WHITESPACE}*"(?P<block_feedback>.*?)"{WHITESPACE}*\n'  # Match 'feedback:', optional whitespace, quoted value, optional whitespace, newline
                                      rf'{WHITESPACE}*html:{WHITESPACE}*\|{WHITESPACE}*\n(?P<block_html>.*?)(?={WHITESPACE}*css:)'  # Match 'html: |', newline, capture content until 'css:'
                                      rf'{WHITESPACE}*css:{WHITESPACE}*\|{WHITESPACE}*\n(?P<block_css>.*?)(?={WHITESPACE}*js:)'  # Match 'css: |', newline, capture content until 'js:'
                                      rf'{WHITESPACE}*js:{WHITESPACE}*\|{WHITESPACE}*\n(?P<block_js>.*?)(?={WHITESPACE}*-\{WHITESPACE}*|\Z)')  # Match 'js: |', newline, capture content until next '-' or end of string (\Z)


            # --- Debugging Print for Block Matches ---
            print(f"Attempting to find code blocks within content...")
            # -----------------------------------------

            for block_match in block_regex.finditer(code_bloks_content):
                print(f"Debug: Found a code block match.")
                block_data = block_match.groupdict()
                # Clean up leading/trailing whitespace from multi-line fields
                for key in ['block_js', 'block_css', 'block_html']:
                     if block_data[key] is not None:
                         block_data[key] = block_data[key].strip()
                # Clean up the feedback string
                if block_data['block_feedback'] is not None:
                     block_data['block_feedback'] = block_data['block_feedback'].strip()
                data['code_bloks'].append(block_data)
        else:
             print("Warning: Could not capture content within code_bloks section brackets. Check for missing ']' or extra content after the last block.")
    else:
        print("Warning: 'code_bloks: [' marker not found. Code blocks section not found or is empty. Check input string format.")


    # Return the Python dictionary
    try:
        # You can optionally return a JSON string if needed, but the function
        # description says return a dictionary.
        # return json.dumps(data, indent=2)
        return data
    except Exception as e:
        print(f"Error returning data dictionary: {e}")
        return None
    
    
################# Convert Code to JSON #####################

def extract_html_blocks(html):
    head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL)
    head_inner = head_match.group(1).strip() if head_match else ""
    html_wo_head = html.replace(head_match.group(0), '') if head_match else html

    pattern = r'<!-- BEGIN (SECTION: )?(?P<name>.*?) -->\s*(?:<!-- DESCRIPTION: (?P<desc>.*?) -->\s*)?(?P<content>.*?)\s*<!-- END (SECTION: )?\1?(?P=name) -->'
    matches = re.finditer(pattern, html_wo_head, re.DOTALL)

    blocks = OrderedDict()
    ordered_names = []

    for match in re.finditer(pattern, html_wo_head, re.DOTALL):
        name = match.group('name').strip()
        description = (match.group('desc') or "").strip()
        content = match.group('content').strip()
        if name not in blocks:
            blocks[name] = {
                "html": content,
                "description": description
            }
            ordered_names.append(name)


    # Optional: handle footer as before
    footer_match = re.search(r'<footer[\s\S]*?</footer>', html_wo_head, re.DOTALL)
    if footer_match and 'footer' not in blocks:
        blocks['footer'] = {
            "html": footer_match.group(0).strip(),
            "description": "Footer section"
        }
        ordered_names.append('footer')
        html_wo_head = html_wo_head.replace(footer_match.group(0), '')

    html_global = re.sub(pattern, '', html_wo_head, flags=re.DOTALL).strip()
    html_global = html_global.replace('</html>', '').strip()

    return head_inner, blocks, html_global, ordered_names

def extract_css_blocks(css):
    pattern = r'/\* BEGIN (SECTION: )?(.*?) \*/(.*?)/\* END (SECTION: )?\2 \*/'
    matches = re.finditer(pattern, css, re.DOTALL)
    blocks = OrderedDict()
    for match in matches:
        name = match.group(2).strip()
        content = match.group(3).strip()
        if name not in blocks:
            blocks[name] = {"css": content}
    css_global = re.sub(pattern, '', css, flags=re.DOTALL).strip()
    return blocks, css_global

def extract_js_blocks(js):
    pattern = r'// BEGIN (SECTION: )?(.*?)\n(.*?)// END (SECTION: )?\2'
    matches = re.finditer(pattern, js, re.DOTALL)
    blocks = OrderedDict()
    for match in matches:
        name = match.group(2).strip()
        content = match.group(3).strip()
        if name not in blocks:
            blocks[name] = {"js": content}
    js_global = re.sub(pattern, '', js, flags=re.DOTALL).strip()
    return blocks, js_global
def parse_custom_format(text):
    html = re.search(r'===SITE_HTML===(.*?)===SITE_CSS===', text, re.DOTALL).group(1).strip()
    css = re.search(r'===SITE_CSS===(.*?)===SITE_JS===', text, re.DOTALL).group(1).strip()
    js = re.search(r'===SITE_JS===(.*)', text, re.DOTALL).group(1).strip()

    head_html, html_blocks, global_html, html_order = extract_html_blocks(html)
    css_blocks, global_css = extract_css_blocks(css)
    js_blocks, global_js = extract_js_blocks(js)

    # Pull out theme_toggle if exists
    theme_html = html_blocks.pop("theme_toggle", {}).get("html", "")
    theme_css = css_blocks.pop("theme_toggle", {}).get("css", "")
    theme_js = js_blocks.pop("theme_toggle", {}).get("js", "")

    # Merge theme_toggle content into global
    merged_global_html = f"{head_html}\n{theme_html}".strip()
    merged_global_css = f"{global_css}\n{theme_css}".strip()
    merged_global_js = f"{global_js}\n{theme_js}".strip()

    seen = set()
    ordered_names = []
    for name in html_order:
        if name not in seen and name != "theme_toggle":
            ordered_names.append(name)
            seen.add(name)
    for d in (css_blocks, js_blocks):
        for name in d:
            if name not in seen and name != "theme_toggle":
                ordered_names.append(name)
                seen.add(name)

    code_bloks = []
    for name in ordered_names:
        if name == "head":
            continue
        code_bloks.append({
            "name": name,
            "html": html_blocks.get(name, {}).get("html", ""),
            "css": css_blocks.get(name, {}).get("css", ""),
            "js": js_blocks.get(name, {}).get("js", ""),
            "feedback": html_blocks.get(name, {}).get("description", "")
        })

    return {
        "global": {
            "name": "global",
            "html": merged_global_html,
            "css": merged_global_css,
            "js": merged_global_js
        },
        "code_bloks": code_bloks
    }





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

