
from langchain_core.prompts import PromptTemplate

create_resume_website_template = """ """

create_resume_website_prompt = PromptTemplate.from_template(create_resume_website_template)


create_resume_website_bloks_template = """You are a professional designer and frontend developer tasked with creating a personal portfolio website for a client based on their resume and preferences with a valid output format required.

the resume information is provided below you may summarize or omit some information if it verbose, to make it more visually appealing and creative:
{resume_yaml}

the client preferences are provided below:
```
{preferences}
```

**REQUIRED Output Format Example:**
```
===HTML===
<head>
<!-- BEGIN head -->
  <!-- here meta, title, favicon, etc. these should be between BEGIN head and END head -->
<!-- END head -->
</head>

<body>
<!-- BEGIN global -->
<!-- DESCRIPTION: This handles global settings, dark mode, light mode, interactive background, overlay, etc. -->
<!-- here in global JUST GLOBAL HTML CODE -->
<!-- END global -->

<!-- BEGIN SECTION: header_and_navigation -->
<!-- DESCRIPTION: This handles the main header with logo and navigation -->
<section id="header_and_navigation">
  <!-- here header content -->
</section>
<!-- END SECTION: header_and_navigation -->

<!-- BEGIN SECTION: hero -->
<!-- DESCRIPTION: ... -->
<section id="hero">
  <!-- here hero content -->
</section>
<!-- END SECTION: hero -->

<!-- Rest of the sections html till footer section in the same format -->
</body>

===CSS===
/* BEGIN global */
/* Here global styles (variables, base styles, themes custom cursor, interactive background,styles uesd in multiple sections, etc.) like global styles, themes, colors, fonts, etc. */
/* DO NOT ADD ANY SECTION SPECIFIC STYLES HERE. EVERY SECTION MUST HAVE ITS OWN STYLES ISOLATED FROM OTHER SECTIONS. BUT YOU CAN ADD GLOBAL STYLES HERE  WHICH WILL BE USED ACROSS ALL SECTIONS */
/* Add the styles which are used in multiple sections here */
/* END global */

/* BEGIN SECTION: header_and_navigation */
/* Header styles */
/* END SECTION: header_and_navigation */

/* BEGIN SECTION: hero */
/* Hero styles */
/* END SECTION: hero */

/* here rest of the sections styles till footer section in the same format */
===JS===
// BEGIN global
// Here global scripts like libraries, frameworks, global animations, global effects, dark mode, light mode etc. these should be between BEGIN global and END global. DO NOT INITIALIZE ANY SECTION RELATED SCRIPTS HERE. EVERY SECTION MUST HAVE ITS OWN SCRIPTS ISOLATED FROM OTHER SECTIONS.
// END global

// BEGIN SECTION: header_and_navigation
// Header scripts
// END SECTION: header_and_navigation

// BEGIN SECTION: hero
// Hero scripts
// END SECTION: hero

// here rest of the sections scripts till footer section in the same format
```

STRICT OUTPUT INSTRUCTIONS
Generate code for a complete single-page website that functions correctly when all sections are combined with global, and also ensures global code plus any single section's code functions correctly when loaded in isolation (for iframe code editor preview).

Output must match the provided format and comments exactly.
===HTML===, ===CSS===, and ===JS=== are unique identifiers and should not be changed or adding multiple times. And must be in the same order.
No explanations, apologies, or extra text before or after the output.
Do not include any code examples, extra comments, or verbose explanations.
All code must be complete and functional—no placeholders, unfinished, or empty sections.
Use emoji favicons.
Enhance the design with icons, 3D visuals, graphics, and illustrations using only HTML, CSS, and JS.
Create original visuals; do not reference external files.
Do not include contact forms or any feature requiring backend integration implement "get in touch" section in creative way.
You may use localStorage or sessionStorage for user preferences, but no backend calls.
The mouse cursor must always be visible, ensure it is visible in dark mode and light mode.
The website must be fully responsive and display correctly on all devices, including mobile-optimized UI patterns like hamburger menus, accordions, tabs, navigation drawers, etc.
All text must be clearly visible and readable in both light and dark modes.
The layout must be clean, consistent, and visually appealing—never cluttered, overlapping, messy, unreadable, or confusing.
All content must be visible and the layout must not be broken.
Add a loading overlay. Include a fixed, full-viewport HTML/CSS overlay with a loading indicator, styled to match the site's design. It should be visible on load and fade out via JS on `window.onload`. 
All JavaScript must work and all sections must function correctly.
Do not initialize section-specific scripts in global JS.
Avoid global event listeners or variables for section scripts. Each section’s JS, CSS, and HTML must be fully self-contained and work independently if loaded in isolation (e.g., in an iframe). Each section must not depend on external scripts or styles.
Do not output anything except the required format.
Do not use file or image paths; all visuals must be created with HTML, CSS, and JS only.
Do not use or create base64 images. Also do not create verbose SVG strings.
**Ensure JavaScript code is correct and functional:** Verify all functions, especially theme toggle function or library imports, are correct and functional. Ensure all functions are called correctly and in the right order.

personal portfolio website output"""

create_resume_website_bloks_prompt = PromptTemplate.from_template(create_resume_website_bloks_template)


edit_resume_website_block_template = """ You are a professional designer and frontend developer tasked with editing a specific section of a personal portfolio website based on a client prompt.
You must output just the updated yaml file with the html, css and js code for the personal portfolio website. Do not output anything else. no comments or explanations.
Do not add any comments in the code. do not use unnecessary tokens in the code.
Pay attention to the yaml output indentation and format.
PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings.
Do not ever use ':' in any of the yaml fields. 
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.
Understand the client prompt and make the necessary changes to the code block. Be specific and concise in your changes.

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
Add this field to the yaml output without any comments:
```yaml
feedback_message: "<here feedback message>" # Interact with user here. Consider that the user will not see the code but will see the changes applied in iframe preview"
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