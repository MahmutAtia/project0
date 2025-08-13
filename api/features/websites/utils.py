from modules.utils import create_auth_dependency
from .chains import create_resume_website_bloks_chain
from fastapi import HTTPException, Header
from typing import Optional
import httpx
import os
import re
import logging

# Configure logging to see output in production environments
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Django service URL
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")



def parse_custom_format(site_text):
    # Extract HTML, CSS, JS blocks
    html_match = re.search(r"===HTML===\s*(.*?)\s*===CSS===", site_text, re.DOTALL)
    css_match = re.search(r"===CSS===\s*(.*?)\s*===JS===", site_text, re.DOTALL)
    js_match = re.search(r"===JS===\s*(.*)", site_text, re.DOTALL)

    if not html_match or not css_match or not js_match:
        missing = []
        if not html_match: missing.append("HTML")
        if not css_match: missing.append("CSS")
        if not js_match: missing.append("JS")
        raise ValueError(f"Parsing failed: Missing required sections: {', '.join(missing)}")

    html = html_match.group(1)
    css = css_match.group(1)
    js = js_match.group(1)

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



# This is the background function
async def generate_website_and_update_django(task_id: str, resume_yaml: str, preferences: dict,
 resume_id:int, user_id:int):
    update_url = f"{DJANGO_API_URL}/api/update-task/"
    generated_website_json = None
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Task {task_id}: Website generation attempt {attempt + 1}/{max_retries}")
            # 1. Run the slow AI generation chain
            generated_website = await create_resume_website_bloks_chain.ainvoke({
                "resume_yaml": resume_yaml,
                "preferences": preferences,
            })
            
            # Add a check to ensure the AI returned a valid string
            if not generated_website or not isinstance(generated_website, str):
                raise ValueError("AI chain failed to return a valid website string.")

            generated_website_json = parse_custom_format(generated_website)
            
            logger.info(f"Task {task_id}: Successfully generated and parsed website on attempt {attempt + 1}.")
            break # Success, exit the retry loop

        except Exception as e:
            last_error = e
            logger.warning(f"Task {task_id}: Attempt {attempt + 1} failed. Error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Task {task_id}: Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Wait for 5 seconds before the next attempt
            else:
                logger.error(f"Task {task_id}: All {max_retries} generation attempts failed.")
                error_payload = {"task_id": task_id, "status": "FAILURE", "error": str(last_error)}
                async with httpx.AsyncClient() as client:
                    await client.post(update_url, json=error_payload)
                return

    if generated_website_json:
        # 2. Update the task in Django with the result
        try:
            payload = {"task_id": task_id, "status": "SUCCESS", "result": {"website": generated_website_json, "resume_id": resume_id}, "user_id": user_id}
            async with httpx.AsyncClient() as client:
                await client.post(update_url, json=payload)
        except Exception as e:
            # 3. If the final update fails, update the task with an error
            logger.error(f"Task {task_id}: Succeeded but failed to update Django. Error: {e}")
            error_payload = {"task_id": task_id, "status": "FAILURE", "error": f"Failed to save result: {e}"}
            async with httpx.AsyncClient() as client:
                await client.post(update_url, json=error_payload)
        

# Create specific dependencies for different features
verify_website_generation = create_auth_dependency("website_generation")
verify_website_edit = create_auth_dependency("resume_section_edit")
