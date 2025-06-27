from langchain_core.prompts import PromptTemplate
import os


template_first_part = """  You are a Human Resources professional tasked with creating a structured YAML file from a resume. The YAML file should be enhanced for professional appeal and include a compelling "about" section. The resume text is provided below:

YAML Template:
```yaml
"""
#  yaml template
with open(os.path.join(os.path.dirname(__file__), "resume.yaml"), "r") as f:
    yaml_template = f.read()

template_last_part = """
’’’

Instructions:

Extract, Interpret, and Enhance: Extract explicit information, interpret context to infer implicit details (without fabrication), and enhance content for a professional and impactful presentation. Use strong action verbs, quantify achievements where possible (without inventing numbers), use concise language, and focus on impact.

"About" Section (Crucial): Create a compelling "about" section (at least 150 words) that provides a personalized overview of the candidate beyond the resume's factual content. This section should:

Capture the candidate's personality, motivations, and career aspirations.
Highlight their unique strengths and what drives them.
Use engaging and professional language.
Synthesize information from the entire resume but avoid simply repeating it. Focus on the "why" behind their choices and experiences.
Imagine this is a brief personal introduction the candidate would give in a networking setting.
Data Mapping, Cleaning, and YAML Output: Map extracted and enhanced information to the YAML template. Perform data cleaning (standardizing dates, handling missing data). Output valid YAML.
PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings and escape ':' s in the yaml output.
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.

Summarization and Objective: Provide a concise, impactful summary and rewrite the objective to be more compelling if needed.

Arrays, Nested Structures, Skill Categorization, and Technologies: Follow previous instructions for handling these elements.

No Fabrication: Do not invent information but enhance and present the candidate's actual experiences and achievements in the best possible light. Try to fill in the missing information as possible.

Simple, Readable, and Impactful Language: Use clear, concise, and professional language throughout.

Use primeicons find the icon that best represents the candidate's profession and include it in the primeicon field.

Output all in the {language} language.

Input Resume Text: {input_text}

Output YAML:"""

create_resume_prompt = (
    PromptTemplate.from_template(template_first_part)
    + yaml_template
    + template_last_part
)