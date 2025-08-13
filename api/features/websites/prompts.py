from langchain_core.prompts import PromptTemplate

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
<!-- DESCRIPTION: This handles global settings, theme toggle, custom cursor, interactive background, overlay, etc. -->
<!-- The theme toggle button and custom cursor elements MUST be placed here to be available in all editor iframes. -->
<div id="custom-cursor"></div>
<button id="theme-toggle" aria-label="Toggle Theme">
  <!-- SVG icons for sun/moon or equivalent -->
</button>
<!-- Other global elements like loading overlay -->
<!-- END global -->

<!-- BEGIN SECTION: header_and_navigation -->
<!-- DESCRIPTION: This handles the main header with logo and navigation -->
<header id="header_and_navigation">
  <nav class="container">
    <!-- here header content -->
  </nav>
</header>
<!-- END SECTION: header_and_navigation -->

<!-- BEGIN SECTION: hero -->
<!-- DESCRIPTION: ... -->
<section id="hero">
  <div class="container">
  <!-- here hero content -->
  </div>
</section>
<!-- END SECTION: hero -->

<!-- Rest of the sections html till footer section in the same format -->
</body>

===CSS===
/* BEGIN global */
/* Here global styles (variables, base styles, themes, custom cursor, etc.) */
/* CRITICAL: For theme switching, apply styles based on an attribute on the <html> tag, like this: html[data-theme='dark'] .some-element {{ ... }} */
/* CRITICAL: The theme toggle button MUST be styled with 'position: fixed' (e.g., bottom-right corner) to be visible in all editor iframes. */
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
// libraries imports must be here
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
**CREATIVE MANDATE**: You must generate a unique, modern, and visually memorable website suitable for a creative professional like a designer or developer. Avoid generic, boring, or repetitive layouts. Prioritize creative interactions, bold typography, and a strong visual identity. The client's preferences are key to unlocking more advanced and creative features.
**IMPORTANT**: To ensure high quality and prevent incomplete output, generate a concise website with a maximum of 8 sections (e.g., Hero, About, Experience, Skills, Contact) plus a header and footer. Focus on quality over quantity.

Generate code for a complete single-page website that functions correctly when all sections are combined with global, and also ensures global code plus any single section's code functions correctly when loaded in isolation (for iframe code editor preview).

Output must match the provided format and comments exactly.
===HTML===, ===CSS===, and ===JS=== are unique identifiers and should not be changed or adding multiple times. And must be in the same order.
No explanations, apologies, or extra text before or after the output.
Do not include any code examples, extra comments, or verbose explanations.
All code must be complete and functional—no placeholders, unfinished, or empty sections.
**CRITICAL CODE QUALITY**: Your generated code, especially within SVG paths or CSS properties, must NOT contain repetitive, nonsensical, or looping patterns. Any such repetition will result in a failed output.
Use emoji favicons.
**SVG USAGE**: Keep all inline SVGs as simple and non-verbose as possible. For icons, prefer single-path SVGs or CSS-only solutions over complex, multi-element SVGs.
Enhance the design with icons, 3D visuals, graphics, and illustrations using only HTML, CSS, and JS.
Create original visuals; do not reference external files.
Do not include contact forms or any feature requiring backend integration implement "get in touch" section in
You may use localStorage or sessionStorage for user preferences, but no backend calls.
The mouse cursor must always be visible, ensure it is visible in dark mode and light mode. **For custom cursors, use `mix-blend-mode: difference;` and a solid color like `white` to ensure visibility on all backgrounds. Do NOT set the cursor's color to be the same as the page's background color.**
The website must be fully responsive and display correctly on all devices, including mobile-optimized UI patterns like hamburger menus, accordions, tabs, navigation drawers, etc.
All text must be clearly visible and readable in both light and dark modes.
The layout must be clean, consistent, and visually appealing—never cluttered, overlapping, messy, unreadable, or confusing.
All content must be visible and the layout must not be broken.
Add a loading overlay. Include a fixed, full-viewport HTML/CSS overlay with a loading indicator, styled to match the site's design. It should be visible on load and fade out via JS.
All JavaScript must work and all sections must function correctly.
Scripts in one section must not depend on or try to directly manipulate elements in another section, unless it's a global system designed to do so (like a navigation menu or scroll animation observer).
**EDITOR COMPATIBILITY**: The editor renders each section in an isolated iframe.
*   **You MUST disable animations that rely on page-level scroll events** (e.g., `window.scrollY`) in the editor, as they will not work correctly. Wrap this logic in a condition like `if (document.body.dataset.renderContext === 'live')`.
*   **You MUST ensure all other self-contained animations** (like typing effects, hover effects, or interactive elements within a single section) **remain active in the editor** to provide an accurate preview.
*   Features that depend on elements from *other* sections (like a navigation link scrolling to an ID) will not work and should be handled gracefully.

**CRITICAL JAVASCRIPT LOGIC**: You must implement logic based on the `data-render-context` attribute on the `<body>` tag. The global script is responsible for handling the loading overlay and all scroll-triggered animations.

1.  **Global JS (`BEGIN global`)**:
    *   Your global script **MUST** check the `data-render-context` to correctly handle the loading overlay and animations.
    *   **Loading Overlay**:
        *   If `document.body.dataset.renderContext === 'editor'`, remove the overlay immediately.
        *   If `document.body.dataset.renderContext === 'live'`, the overlay must be visible for a minimum of 1.5 seconds and wait for the page to fully load before fading out.
    *   **Scroll Animations**:
        *   Create a single, global `IntersectionObserver` that targets all elements with a common class (e.g., `.animate-on-scroll`).
        *   If in the `'editor'`, immediately add the `.is-visible` class to all animated elements so they appear in the preview without needing to scroll.
        *   If in `'live'`, use the observer to add the `.is-visible` class as elements scroll into view.
    *   **Example Logic**:
        ```javascript
        const isEditor = document.body.dataset.renderContext === 'editor';

        // --- Loading Overlay ---
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {{
            if (isEditor) {{
                loadingOverlay.style.display = 'none';
            }} else {{
                const minDisplayTime = new Promise(resolve => setTimeout(resolve, 1500));
                const pageLoad = new Promise(resolve => window.addEventListener('load', resolve));
                Promise.all([minDisplayTime, pageLoad]).then(() => {{
                    loadingOverlay.style.opacity = '0';
                    setTimeout(() => {{ loadingOverlay.style.display = 'none'; }}, 500);
                }});
            }}
        }}

        // --- Theme Toggle (safe check) ---
        // Ensure the theme toggle button exists before adding the event listener
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {{
            themeToggle.addEventListener('click', () => {{
                // This is just an example, the AI will implement the actual logic
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
            }});
        }}

        // --- Custom Cursor (safe check) ---
        // This feature is self-contained and should work in the editor.
        const customCursor = document.getElementById('custom-cursor');
        if (customCursor) {{
             window.addEventListener('mousemove', e => {{
                customCursor.style.left = e.clientX + 'px';
                customCursor.style.top = e.clientY + 'px';
            }});
        }}

        // --- Interactive Background (safe check) ---
        // This feature is self-contained and should work in the editor.
        const interactiveBg = document.getElementById('interactive-background');
        if (interactiveBg) {{
            // AI will implement the canvas animation logic here.
            // It should NOT be disabled in the editor.
        }}

        // --- Global Scroll Animation Handler ---
        const animatedElements = document.querySelectorAll('.animate-on-scroll');
        if (isEditor) {{
            // In editor mode, all animated elements in the current iframe should be visible.
            animatedElements.forEach(el => el.classList.add('is-visible'));
        }} else {{
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        entry.target.classList.add('is-visible');
                        observer.unobserve(entry.target);
                    }}
                }});
            }}, {{ threshold: 0.1 }});
            animatedElements.forEach(el => observer.observe(el));
        }}
        ```
2.  **Section JS (e.g., `BEGIN SECTION: about`)**:
    *   Section-specific JavaScript should ONLY contain logic for features unique to that section (e.g., an accordion, a carousel, a specific button interaction).
    *   **DO NOT** include any scroll animation or IntersectionObserver logic here. This is now handled globally.

Do not output anything except the required format.
Do not use file or image paths; all visuals must be created with HTML, CSS, and JS only.
Do not use or create base64 images. Also do not create verbose SVG strings.
**Ensure JavaScript code is correct and functional:** Verify all functions, especially theme toggle function or library imports, are correct and functional. Ensure all functions are called correctly and in the right order.
DO NOT use infinite loops or recursive functions
DO NOT use setInterval or setTimeout without clearInterval/clearTimeout
DO NOT use document.write() or document.open()
DO NOT use window.location redirects
DO NOT use excessive DOM manipulation in loops
DO NOT use heavy animations or continuous effects
DO NOT use eval() or Function() constructor
DO NOT create memory leaks with event listeners
ENSURE all scripts have error handling (try-catch)
ENSURE animations are lightweight and finite
ENSURE scripts complete execution quickly (under 2 seconds)
IF using event listeners, provide cleanup methods
IF using animations, use CSS instead of JavaScript when possible
**CRITICAL**: Do NOT wrap your JavaScript code in `DOMContentLoaded` or `window.onload` event listeners. The scripts are already placed at the end of the body, so the DOM is ready.
**CRITICAL**: All scroll-triggered animations must be handled by a single, global IntersectionObserver that targets a common class like `.animate-on-scroll`. Do NOT create separate observers in each section.
personal portfolio website output"""

create_resume_website_bloks_prompt = PromptTemplate.from_template(
    create_resume_website_bloks_template
)


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
edit_website_block_prompt = PromptTemplate.from_template(
    edit_resume_website_block_template
)

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



# **CREATIVE FEATURES & ADVANCED INTERACTIONS**:
# If the client's preferences mention specific keywords, implement the corresponding advanced features:
# - **"Magnetic buttons" or "magnetic elements"**: Make specified elements (like buttons or links) attract the custom cursor when it's nearby.
# - **"Text reveal animation"**: Animate headlines or key text to appear letter by letter or word by word on scroll.
# - **"Scroll-based rotation/scaling"**: Animate images or decorative elements to rotate or scale as the user scrolls through a section.
# - **"Unconventional grid" or "asymmetrical layout"**: Use overlapping elements and a non-standard grid to create a more dynamic and less rigid design.
# - **"Advanced hover effects"**: Implement unique hover effects on portfolio items or cards, like image distortions, color shifts, or content reveals.
