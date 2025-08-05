# Import chain_instance from the resumes chains module
import sys
import os
from .prompts import create_resume_website_bloks_prompt
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from resumes.chains import chain_instance


create_resume_website_bloks_chain = chain_instance.build_chain(
    create_resume_website_bloks_prompt, model="gemini-2.0-flash"
)