from langchain_core.prompts import PromptTemplate
import os

#  yaml template
with open(os.path.join(os.path.dirname(__file__), "resume.yaml"), "r") as f:
    yaml_template = f.read()

template = """  You are a Human Resources professional tasked with modifing a structured YAML file for a resume. The YAML file should be enhanced for professional appeal and include a compelling "about" section.

Instructions:

Extract, Interpret, and Enhance: Extract explicit information, interpret context to infer implicit details (without fabrication), and enhance content for a professional and impactful presentation. Use strong action verbs, quantify achievements where possible (without inventing numbers), use concise language, and focus on impact.

"about_candidate" Section (Crucial): Create a compelling "about_candidate" section (at least 150 words) that provides a personalized overview of the candidate beyond the resume's factual content. This section should:
Capture the candidate's personality, motivations, and career aspirations.
Highlight their unique strengths and what drives them.

Use engaging and professional language.
Synthesize information from the entire resume but avoid simply repeating it. Focus on the "why" behind their choices and experiences.
Imagine this is a brief personal introduction the candidate would give in a networking setting.
Data Mapping, Cleaning, and YAML Output: Map extracted and enhanced information to the YAML template. Perform data cleaning (standardizing dates, handling missing data). Output valid YAML.


Summarization and Objective: Provide a concise, impactful summary and rewrite the objective to be more compelling if needed.

Arrays, Nested Structures, Skill Categorization, and Technologies: Follow previous instructions for handling these elements.

No Fabrication: Do not invent information but enhance and present the candidate's actual experiences and achievements in the best possible light. Try to fill in the missing information as possible.

Simple, Readable, and Impactful Language: Use clear, concise, and professional language throughout.

PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings and escape ':' s in the yaml output.
PAY ATTENTION to all yaml parsing rules and indentation.
When using "'" it must escaped with a "''" like this: "I''m a software engineer"
Do not output any yaml comments in the output.

Output all in the {language} language.

Input Resume Text: {input_text}

Target Job Description: {job_description}

User Extra Instructions: {instructions}

Output YAML:"""

create_resume_prompt = (
    PromptTemplate.from_template(template)
)



edit_resume_section_template = """  You are a Human Resources professional tasked with editing a specific section of a structured YAML file created from a resume.
Understand Candidate's Prompt: Read the candidate's prompt to understand the context and requirements for the section you will edit. the candidate's prompt is provided to guide your editing of filling information in the {section_title} section according to the candidate's requirements.
Output only the section you are editing in the YAML file. Do not output anything else. no comments or explanations.
If the prompt is very irrelevant or not clear, you can output an example of the section you are editing in the YAML file.
PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings and escape ':' s in the yaml output.
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.

Provided Section yaml to edit:
```yaml
{section_yaml}
```
Candidate's Prompt:{prompt}
Output YAML:"""


edit_resume_section_prompt = PromptTemplate.from_template(edit_resume_section_template)



####################################

create_template_first_part = """  You are a Human Resources professional tasked with creating a structured YAML file from a resume. The YAML file should be enhanced for professional appeal and include a compelling "about" section. The resume text is provided below:

YAML Template:
```yaml
"""

create_template_last_part = """
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

ATS Evaluation Result For Candidate Current Resume:
{ats_result}

Input Resume Text: {input_text}

Output YAML:"""

ats_create_resume_prompt = (
    PromptTemplate.from_template(create_template_first_part)
    + yaml_template
    + create_template_last_part
)


#########################################


job_desc_template_first_part = """  You are a Human Resources professional tasked with creating a structured YAML file from a resume. The YAML file should be enhanced for professional appeal and include a compelling "about" section. The resume text is provided below:

YAML Template:
```yaml
"""


job_desc_template_last_part = """
’’’

Instructions:

Extract, Interpret, and Enhance: Extract explicit information, interpret context to infer implicit details (without fabrication), and enhance content for a professional and impactful presentation. Use strong action verbs, quantify achievements where possible (without inventing numbers), use concise language, and focus on impact.

"About" Section (Crucial): Create a compelling "about" section (at least 100 words) that provides a personalized overview of the candidate beyond the resume's factual content. This section should:

Capture the candidate's personality, motivations, and career aspirations.
Highlight their unique strengths and what drives them.
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

Do not output any comments or and other explanations just the YAML file.

Output all in the {language} language.

Tailor the resume to the job description provided below, ensuring that the candidate's skills and experiences are aligned with the job requirements. Use the job description to guide your enhancements and ensure the resume is tailored to the job.

job description:
{job_description}

ATS Evaluation Result For Candidate Current Resume:
{ats_result}

Input Resume Text: {input_text}
Output YAML:"""

ats_job_desc_resume_prompt = (
    PromptTemplate.from_template(job_desc_template_first_part)
    + yaml_template
    + job_desc_template_last_part
)




###################### ATS Checker ######################

ats_checker_template = """ You are an Applicant Tracking System (ATS) Resume Evaluator.

Evaluate the candidate's resume against the job description below. Return your analysis in the following format:

---
🏆 OVERALL SCORE: [score]/100

🧩 COMPONENT SCORES:
- Skills Match: [score]/40
- Experience Relevance: [score]/20
- Education Fit: [score]/10
- Contact Info & Formatting: [score]/10
- Keyword Match: [score]/10
- Overall Language Relevance: [score]/10

🛠️ STRENGTHS:
[List key strengths found in the resume, such as strong technical skills, leadership experience, etc.]

⚠️ WEAKNESSES:
[List weaknesses or issues found in the resume, such as missing keywords, unclear formatting, or lack of relevant experience.]

💡 ADVICE:
[Give clear and concise advice on how to improve the resume to better match the job description.]

---

- The output must be maximum 200 words.
- do not output "#" s in the output. but you can use "•" or "*" or "-" instead.
- The output should be in markdown formated and do not output any other text, comments or any other explanations.
- The output should be very short and concise.
- The output should be in the {language} language.

Target role: "{user_input_role}"

Here is the job description:

{job_description}

Here is the resume text:
{input_text}

the evaluation output: """

ats_checker_prompt = PromptTemplate.from_template(ats_checker_template)


ats_checker_no_job_desc_template = """You are an ATS Resume Evaluator. A user has uploaded a resume and wants to know how well it would perform in a real-world ATS system.

Evaluate the resume based on general job market standards and the target role (if provided). Return your analysis in the following format:
---
🏆 OVERALL SCORE: [score]/100

🧩 COMPONENT SCORES:
- Skills Relevance: [score]/30  
- Experience Quality & Clarity: [score]/20
- Education & Certifications: [score]/10
- Formatting & Readability: [score]/20
- ATS-Friendliness: [score]/10
- Clarity of Career Direction: [score]/10

🎯 TARGET ROLE: [target_role or "Not specified"]

🛠️ STRENGTHS:
[List the strongest elements of the resume.]

⚠️ WEAKNESSES:
[List the weakest elements or common red flags.]

💡 ADVICE:
[Provide actionable, practical advice for improving the resume.] 
---

- The output must be maximum 200 words.
- do not output "#" s in the output. but you can use "•" or "*" or "-" instead.
- The output should be in markdown formated and do not output any other text, comments or any other explanations.
- The output should be very short and concise.
- The output should be in the {language} language.

Here is the resume text:

{input_text}

Target role: "{user_input_role}"

the evaluation output: """

ats_checker_no_job_desc_prompt = PromptTemplate.from_template(
    ats_checker_no_job_desc_template
)
