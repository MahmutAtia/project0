
from langchain_core.prompts import PromptTemplate

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

PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings and escape ':' s in the yaml output.
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.


Client Preferences:
{preferences}

personal website yaml output"""

create_resume_website_prompt = PromptTemplate.from_template(create_resume_website_template)
create_resume_website_bloks_template = """ You are a website generation AI.
Based on the user's resume and preferences, generate the structure of a personal website with valid output format.

the resume information is provided below:
{resume_yaml}

the user preferences are provided below:
{preferences}


**REQUIRED Output Format Example:**
```
===SITE_HTML===
<!-- BEGIN head -->
<head>
  <!-- here fonts meta, title, etc. also add dark and light mode toggle -->
</head>
<!-- END head -->
<body>
<!-- BEGIN theme_toggle  -->
<!-- here theme_toggle  -->
<!-- END theme_toggle  -->

<!-- BEGIN SECTION: header -->
<!-- DESCRIPTION: This handles the main header with logo and navigation -->
<section id="header">
  <!-- here header content -->
</section>
<!-- END SECTION: header -->

<!-- BEGIN SECTION: hero -->
<!-- DESCRIPTION: ... -->
<section id="hero">
  <!-- here hero content -->
</section>
<!-- END SECTION: hero -->

<!-- Rest of the sections -->
</body>
===SITE_CSS===
/* GLOBAL */
/* Here global styles (variables, base styles, themes)*/
/* DO NOT ADD ANY SECTION SPECIFIC STYLES HERE. EVERY SECTION MUST HAVE ITS OWN STYLES ISOLATED FROM OTHER SECTIONS. BUT YOU CAN ADD GLOBAL STYLES HERE  WHICH WILL BE USED ACROSS ALL SECTIONS */

/* BEGIN theme_toggle */
/* Theme toggle styles */
/* END theme_toggle */

/* BEGIN SECTION: header \*/
/* Header styles */
/* END SECTION: header \*/

/* BEGIN SECTION: hero */
/* Hero styles */
/* END SECTION: hero \*/
===SITE_JS===
// GLOBAL
// Here global scripts
// DO NOT INITIALIZE ANY SECTION RELATED SCRIPTS HERE. EVERY SECTION MUST HAVE ITS OWN SCRIPTS ISOLATED FROM OTHER SECTIONS.

// BEGIN theme_toggle
// Theme toggle scripts
// END theme_toggle

// BEGIN SECTION: header
// Header scripts
// END SECTION: header

// BEGIN SECTION: hero
// Hero scripts
// END SECTION: hero
```
I also need to follow a very specific set of negative constraints regarding the output format:

No explanatory text, apologies, or extra characters before or after the output format.
Use the same format and comments as the example.
No other types of comments or explanations.
No examples in code.
No unfinished code; all functionalities must be complete and working.
Add favicons, icons, 3d visuals, graphics, and illustrations to enhance the design.
No empty placeholders or incomplete sections.
No contact forms which need backend integration. This is a static website.
You may use local storage or session storage for storing user preferences or data, but no backend integration.
Do not initialize any section related scripts in global js. Every section must be working fine if i parsed the output and add it to iframe which has global js, css and html and one of any of section js, css and html. This is very important.


personal portfolio website yaml output"""

create_resume_website_bloks_prompt = PromptTemplate.from_template(create_resume_website_bloks_template)


edit_resume_website_block_template = """ You are a professional designer and frontend developer tasked with editing a specific section of a personal portfolio website based on a client prompt.
You must output just the updated yaml file with the html, css and js code for the personal portfolio website. Do not output anything else. no comments or explanations.
Do not add any comments in the code. do not use unnecessary tokens in the code.
Pay attention to the yaml output indentation and format.
PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings.
Do not ever use ':' in any of the yaml fields. 
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.

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
  
  

"""
Structure:
A global object:

name: always "global"

feedback: Short explanation for the user (max 100 characters) about what to edit in this section

js: Global JavaScript (e.g. libraries, frameworks, animations, effects, dark mode, light mode) will be rendered between <script> and </script> tags. Do not add any sections related js here it must be added in the code bloks

css: Global styles (global styles, themes, colors, fonts, etc.) don't add any section related css here it must be added in the code bloks

html: Global <head> elements (meta tags, favicon, fonts, dark mode, light mode, etc.) do not add any sections html here or any other visual elements.

A code_bloks array. Each object includes: will be rendered between <body> and </body> tags. Do not add any global html code here it must be added in the global object.

name: Section identifier (e.g. "header", "hero_section", "about", "projects", etc.) there is no blok called global.

feedback: Short user-facing comment on what the section does (max 100 characters)

html, css, js: Code for that block.
"""

"""
The code structure is defined by an object containing two main parts: a single `global` object and a `code_blocks` array.

**1. The `global` Object:**
This object holds code and configurations that apply globally to the entire website. It will be used to construct the document's `<head>` and include global CSS and JavaScript files/code.

* **`name`**: Always set to the string "global".
* **`feedback`**: A short explanation for the user (maximum 100 characters) describing the purpose of this global configuration section (e.g., "Manage global settings and head elements").
* **`js`**: Global JavaScript code (e.g., libraries, frameworks setup, site-wide animation triggers, dark/light mode logic that isn't tied to a specific visual component). This code will be rendered within `<script>` tags. **Do NOT include JavaScript code specific to individual sections or components here.**
* **`css`**: Global CSS styles (e.g., CSS variables, base styles, typography defaults, theme definitions, global utility classes). This code will be rendered within `<style>` tags or linked as a stylesheet. **Do NOT include CSS styles specific to individual sections or components here.**
* **`html`**: Global `<head>` elements (e.g., `<meta>` tags, `<link>` tags for favicons or fonts, `<title>`). **Do NOT include any `<body>` content, visual elements, or section-specific HTML within this field. just add light and dark mode toggle buttons here.

**2. The `code_blocks` Array:**
This array contains multiple objects, where each object represents a distinct section or component that will be rendered sequentially within the document's `<body>`.

* This array will be used to render content **between `<body>` and `</body>` tags.** **Do NOT add any global HTML structure (like `<html>`, `<head>`, or `<body>` tags themselves) here.**
* Each object within the `code_blocks` array must include:
    * **`name`**: A unique identifier for the section (e.g., "header", "hero_section", "about_me", "projects_list", "contact_form"). **The name "global" is reserved for the global object and should NOT be used as a section name here.**
    * **`feedback`**: A short user-facing comment (maximum 100 characters) explaining what content or functionality this specific section block provides (e.g., "Website header and navigation", "Introduction section with hero image").
    * **`html`**: The HTML code specifically for this section block.
    * **`css`**: The CSS code specifically for styling *only* this section block.
    * **`js`**: The JavaScript code specifically for functionality *only* within this section block.
"""

# I did not like most of design concepts results 

# you must think of modern creative pesonal sites for designers and frontend developers and then draw the design concepts

# also think of list of prefrejnces that the user can choose from to make the website more visually appealing and creative. and all of them add certain instructions to the PromptTemplate

# - for example the design concepts after doing the refinement make them different 5 design concepts 
# - somethings like cheklist adding then will add instructions like the cursor animation trick think of other tricks and things which are widly uesed in pesonal websites
# - think of other themes and colors and fonts that are widely used in personal websites
# - i waht ther preferences that will make perfect personal websites and the most visually appealing and creative and unique authentic fot this specific user