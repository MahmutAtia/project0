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

Summarization and Objective: Provide a concise, impactful summary and rewrite the objective to be more compelling if needed.

Arrays, Nested Structures, Skill Categorization, and Technologies: Follow previous instructions for handling these elements.

No Fabrication: Do not invent information but enhance and present the candidate's actual experiences and achievements in the best possible light. Try to fill in the missing information as possible.

Simple, Readable, and Impactful Language: Use clear, concise, and professional language throughout.

Use primeicons find the icon that best represents the candidate's profession and include it in the primeicon field.

Input Resume Text: {input_text}
Output YAML:"""

create_resume_prompt = (
    PromptTemplate.from_template(template_first_part)
    + yaml_template
    + template_last_part
)


#########################################



job_desc_template_first_part = """  You are a Human Resources professional tasked with creating a structured YAML file from a resume. The YAML file should be enhanced for professional appeal and include a compelling "about" section. The resume text is provided below:

YAML Template:
```yaml
"""
#  yaml template
with open(os.path.join(os.path.dirname(__file__), "resume.yaml"), "r") as f:
    yaml_template = f.read()

job_desc_template_last_part = """
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

Summarization and Objective: Provide a concise, impactful summary and rewrite the objective to be more compelling if needed.

Arrays, Nested Structures, Skill Categorization, and Technologies: Follow previous instructions for handling these elements.

No Fabrication: Do not invent information but enhance and present the candidate's actual experiences and achievements in the best possible light. Try to fill in the missing information as possible.

Simple, Readable, and Impactful Language: Use clear, concise, and professional language throughout.

Use primeicons find the icon that best represents the candidate's profession and include it in the primeicon field.

Do not output any comments or and other explanations just the YAML file.

Output all in the {language} language.

{docs_instructions}

Tailor the resume to the job description provided below, ensuring that the candidate's skills and experiences are aligned with the job requirements. Use the job description to guide your enhancements and ensure the resume is tailored to the job.

{job_description}

Input Resume Text: {input_text}
Output YAML:"""

job_desc_resume_prompt = (
    PromptTemplate.from_template(job_desc_template_first_part)
    + yaml_template
    + job_desc_template_last_part
)





########################################




edit_resume_section_template = """  You are a Human Resources professional tasked with editing a specific section of a structured YAML file created from a resume.
Understand Candidate's Prompt: Read the candidate's prompt to understand the context and requirements for the section you will edit. the candidate's prompt is provided to guide your editing of filling information in the {section_title} section according to the candidate's requirements.
Output only the section you are editing in the YAML file. Do not output anything else. no comments or explanations.
If the prompt is very irrelevant or not clear, you can output an example of the section you are editing in the YAML file.

Provided Section yaml to edit:
```yaml
{section_yaml}
```
Candidate's Prompt:{prompt}
Output YAML:"""


edit_resume_section_prompt =  PromptTemplate.from_template(edit_resume_section_template)

create_resume_website_template = """ You are a professional designer and frontend developer tasked with creating a structured YAML file which contains the html,css and js code for a personal portfolio website based on a resume. . The website should be enhanced for professional appeal and include a compelling "about" section. 

yaml output format:
```yaml
html: "html code here"
css: "css code here"
js: "js code here"
```

the resume information is provided below:
YAML Template:
```yaml
{resume_yaml}
```
Instructions:
- Be creative and innovative in your design.
- Use modern design principles and best practices.
- Ensure the website is responsive and works well on different devices.
- Use fonts and colors that are suitable for the candidate's profession.
- Use high-quality images and graphics to enhance the design.
- Use iconography and illustrations to support the content.
- Use icons to enhance the visual appeal.
- Ensure the website is optimized for performance.
- Use valid HTML, CSS, and JS code.
- Make it easy to navigate and user-friendly.
- Ensure the website is visually appealing.
- use colors and fonts that are suitable for the candidate's profession.
- use animated transitions and effects to enhance the user experience.
- use animations and artistic elements to make the website more engaging.
- make it realy visually appealing and creative.
- Use modern design trends and techniques to create a unique and memorable website.
- You may not use all the information in the resume yaml file, but use the most relevant and important information to create a visually appealing and creative website.
- You may summarize or omit some information to make it more visually appealing and creative.
- Ensure that all card and visual elements have a consistent design and style. Also add effects, animate and hover effects to the cards and visual elements.
Client Preferences:
{preferences}

personal website yaml output"""

create_resume_website_prompt = PromptTemplate.from_template(create_resume_website_template)
create_resume_website_bloks_template = """ You are a professional designer and frontend developer tasked with creating a structured YAML file which contains the html,css and js code for a personal portfolio website based on a client resume information.
Just output the yaml file with the html, css and js code for the personal portfolio website. Do not output anything else. no comments or explanations.
Do not add any comments in the code. do not use unnecessary tokens in the code.
Ensure initial content visibility in CSS and use JavaScript to dynamically add hiding/animation classes for progressive enhancement.
Pay attention to the yaml output indentation and format.


yaml output example format:s
```yaml
global:
  name: "global"
  js: | 
    # global js code here. global js code will be rendered between <script> and </script> tags. Here you can add global js code like libraries, frameworks, etc. also global animations and effects.
  css: | 
    # global css and themes code here
  html: | 
    # global html code here. This global html will be rendered between <head> and </head> tags. Here you can add global html code like meta tags, title, favicon, fonts links, etc.
  feedback: "Here you can modify the global styles and themes for the website." # short feedback for the client max 100 characters
code_bloks: # examples of code bloks. you should add bloks according to the resume information and the client preferences.
  - name: "header"
    html: | 
      # header html code here
    css: | 
      # header css code here
    js: | 
      # header js code here
    feedback: "here you can modify the header of the website." # short feedback for the client max 100 characters
  - name: "hero_section"
    html: | 
      # hero section html code here
    css: | 
      # hero section css code here
    js: | 
      # hero section js code here
    feedback: "Hero section."
```

 

 
the resume information is provided below:
YAML Template:
```yaml
{resume_yaml}
```

Client Preferences:
{preferences}

Instructions: 
Pay attention to the following points in your design:
Visually compelling & modern design.
Reflect professional identity (based on resume).
Prioritize key resume info; summarize/omit as needed.
Clean layout, strong visual hierarchy.
High-quality, relevant images/graphics.
Strategic use of consistent icons/illustrations.
Visually appealing & memorable.
Modern design trends & techniques.
Intuitive navigation, responsive design.
Subtle, tasteful animated transitions/effects.
Engaging hover/animation on interactive elements.
User-friendly experience.
Valid HTML5, CSS3, efficient JS.
Optimize for fast loading.
Consistent design across all elements.

personal portfolio website yaml output"""

create_resume_website_bloks_prompt = PromptTemplate.from_template(create_resume_website_bloks_template)


edit_resume_website_block_template = """ You are a professional designer and frontend developer tasked with editing a specific section of a personal portfolio website based on a client prompt.
You must output just the updated yaml file with the html, css and js code for the personal portfolio website. Do not output anything else. no comments or explanations.
Do not add any comments in the code. do not use unnecessary tokens in the code.
Pay attention to the yaml output indentation and format.

the yaml to edit:
```yaml
name: "{current_name}"
html: |
{current_html}
css: |
{current_css}
js: |
{current_js}
```
here also some artifacts that user added you can use them to edit the yaml:
{artifacts}

Client Prompt: {prompt}
Updated yaml output:"""
edit_website_block_prompt = PromptTemplate.from_template(edit_resume_website_block_template)

