
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
create_resume_website_bloks_template = """ You are a professional designer and frontend developer tasked with creating a structured YAML file which contains the html,css and js code for a personal portfolio website based on a client resume information.
Just output the yaml file with the html, css and js code for the personal portfolio website. Do not output anything else. no comments or explanations.
Do not add any comments in the code. do not use unnecessary tokens in the code.
Ensure initial content visibility in CSS and use JavaScript to dynamically add hiding/animation classes for progressive enhancement.
Pay attention to the yaml output indentation and format.
PAY ATTENTION, Quote all strings in the yaml output with double quotes. Use | for multiline strings.
Do not ever use ':' in any of the yaml fields. 
PAY ATTENTION to all yaml parsing rules and indentation.
Do not output any yaml comments in the output.

yaml output example format:
```yaml
global:
  name: "global"
  feedback: "Here you can modify the global styles and themes for the website." # short feedback for the client max 100 characters
  js: | 
    # global js code here. global js code will be rendered between <script> and </script> tags. Here you can add global js code like libraries, frameworks, etc. also global animations and effects.
  css: | 
    # global css and themes code here
  html: | 
    # global html code here. This global html will be rendered between <head> and </head> tags. Here you can add global html code like meta tags, title, favicon, fonts links, etc.
code_bloks: # examples of code bloks. you should add bloks according to the resume information and the client preferences.
  - name: "header"
    feedback: "here you can modify the header of the website." # short feedback for the client max 100 characters
    html: | 
      # header html code here
    css: | 
      # header css code here
    js: | 
      # header js code here
  - name: "hero_section"
    feedback: "Hero section."
    html: | 
      # hero section html code here
    css: | 
      # hero section css code here
    js: | 
      # hero section js code here
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


use something like this:
Okay, here is a prompt you can use to request a similar portfolio site structure and styling. This prompt aims to capture the key elements you highlighted as making the provided site beautiful and modern.

```
Create a responsive personal portfolio website using HTML, CSS, and JavaScript using style like these:
:root 
    --primary-color: #34495e; /* Deep Blue/Charcoal */
    --secondary-color: #5fa2e0; /* Lighter Blue Accent */
    --text-color: #333;
    --light-text-color: #666;
    --background-color: #f4f7f6; /* Light Gray */
    --card-background: #fff;
    --border-color: #ddd;
    --shadow-color: rgba(0, 0, 0, 0.1);
    --heading-font: 'Poppins', sans-serif;
    --body-font: 'Open Sans', sans-serif;
    --border-radius: 8px;
    --transition-speed: 0.3s ease-in-out;


/* General Styles */
* 
    margin: 0;
    padding: 0;
    box-sizing: border-box;


body 
    font-family: var(--body-font);
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
    scroll-behavior: smooth;


.container 
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;


section 
    padding: 80px 0;
    position: relative; /* Needed for scroll animation */


.section-description 
    text-align: center;
    margin-bottom: 40px;
    font-size: 1.1em;
    color: var(--light-text-color);


.light-background 
    background-color: var(--background-color);


h1, h2, h3, h4, h5, h6 
    font-family: var(--heading-font);
    color: var(--primary-color);
    margin-bottom: 0.5em;
    line-height: 1.2;


h2 
    text-align: center;
    font-size: 2.5em;
    margin-bottom: 20px;
    position: relative;
    display: block; /* Ensure underline spans width */

h2::after 
    content: '';
    display: block;
    width: 60px;
    height: 4px;
    background: var(--secondary-color);
    margin: 10px auto 0;
    border-radius: 2px;


a 
    color: var(--secondary-color);
    text-decoration: none;
    transition: color var(--transition-speed);

a:hover 
    color: var(--primary-color);


.btn 
    display: inline-block;
    padding: 12px 25px;
    background: var(--secondary-color);
    color: #fff;
    border: none;
    border-radius: var(--border-radius);
    font-family: var(--heading-font);
    font-size: 1em;
    cursor: pointer;
    transition: background var(--transition-speed), transform var(--transition-speed);
    text-align: center;


.btn:hover 
    background: #4a8ac7; /* Darker secondary color */
    transform: translateY(-2px);


.card 
    background: var(--card-background);
    border-radius: var(--border-radius);
    box-shadow: 0 4px 8px var(--shadow-color);
    padding: 30px;
    transition: transform var(--transition-speed), box-shadow var(--transition-speed);
    height: 100%; /* Ensure equal height in grid */
    display: flex;
    flex-direction: column;


.card:hover 
    transform: translateY(-10px);
    box-shadow: 0 8px 16px var(--shadow-color);


.card-header 
    display: flex;
    align-items: center;
    margin-bottom: 15px;


.card-icon 
    font-size: 1.8em;
    color: var(--secondary-color);
    margin-right: 15px;


.card h3 
    margin: 0;
    font-size: 1.4em;
    color: var(--primary-color);


.icon-color 
    color: var(--secondary-color);
    margin-right: 8px;


.icon-small 
     font-size: 0.9em;
     margin-right: 5px;
     color: var(--light-text-color);


/* Header & Navigation */
header 
    background: var(--card-background);
    padding: 15px 0;
    position: fixed;
    width: 100%;
    top: 0;
    left: 0;
    z-index: 1000;
    box-shadow: 0 2px 4px var(--shadow-color);


header .container 
    display: flex;
    justify-content: space-between;
    align-items: center;


.logo 
    font-family: var(--heading-font);
    font-size: 1.8em;
    font-weight: 700;
    color: var(--primary-color);


nav ul 
    list-style: none;
    display: flex;


nav ul li 
    margin-left: 30px;


nav ul li a 
    font-family: var(--heading-font);
    font-weight: 600;
    color: var(--text-color);
    font-size: 1em;
    transition: color var(--transition-speed);
    position: relative;


nav ul li a::after 
    content: '';
    position: absolute;
    left: 0;
    bottom: -5px;
    width: 0;
    height: 2px;
    background: var(--secondary-color);
    transition: width var(--transition-speed);


nav ul li a:hover::after 
    width: 100%;


.nav-toggle 
    display: none; /* Hide on desktop */
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    position: relative;
    z-index: 1001; /* Above nav */


.hamburger 
    display: block;
    position: relative;


.hamburger, .hamburger::before, .hamburger::after 
    width: 30px;
    height: 3px;
    background: var(--primary-color);
    border-radius: 3px;
    transition: transform var(--transition-speed), opacity var(--transition-speed);


.hamburger::before, .hamburger::after 
    content: '';
    position: absolute;
    left: 0;


.hamburger::before 
    top: -8px;


.hamburger::after 
    top: 8px;


.nav-open .hamburger 
    transform: rotate(45deg);


.nav-open .hamburger::before 
    opacity: 0;


.nav-open .hamburger::after 
    top: 0;
    transform: rotate(-90deg);


/* Hero Section */
#hero 
    background: linear-gradient(to right, var(--primary-color) 0%, #2c3e50 100%); /* Dark gradient */
    color: #fff;
    padding: 120px 0 80px; /* Adjust padding considering fixed header */
    display: flex;
    align-items: center;
    min-height: 80vh; /* Make it taller */


#hero .container 
    display: flex;
    align-items: center;
    gap: 50px;


.hero-content 
    flex: 1;


.hero-content h1 
    font-size: 3.5em;
    margin-bottom: 10px;
    color: #fff;


.hero-content .subtitle 
    font-size: 1.5em;
    margin-bottom: 20px;
    color: var(--secondary-color);
    font-family: var(--heading-font);


.hero-description p 
    font-size: 1.1em;
    margin-bottom: 15px;
    color: rgba(255, 255, 255, 0.9);


.hero-graphic 
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;


.graphic-shape 
    width: 250px;
    height: 250px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%; /* Example shape */
    position: absolute;
    animation: pulse 2s infinite alternate;


.hero-graphic i 
    font-size: 10em;
    color: var(--secondary-color);
    position: relative;
    z-index: 2;


@keyframes pulse 
    0%  transform: scale(0.95); 
    100%  transform: scale(1); 


/* About Section */
#about .about-content 
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 40px;
    align-items: start;


.about-text p 
    margin-bottom: 15px;
    font-size: 1.1em;
    line-height: 1.7;


.about-skills-summary .icon-color 
     font-size: 1.2em;

.about-skills-summary h3 
     margin-bottom: 15px;
     font-size: 1.5em;
     border-bottom: 2px solid var(--secondary-color);
     padding-bottom: 5px;

.about-skills-summary ul 
    list-style: none;
    padding: 0;

.about-skills-summary li 
    margin-bottom: 10px;
    font-size: 1.1em;


/* Experience and Education Grids */
.experience-grid, .education-grid 
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 30px;


.experience-card .company, .education-card .institution 
    font-weight: 600;
    margin-bottom: 5px;
    color: var(--primary-color);
    font-size: 1.1em;


.experience-card .dates, .education-card .dates 
    font-size: 0.9em;
    color: var(--light-text-color);
    margin-bottom: 10px;


.experience-card .location 
     font-size: 0.9em;
     color: var(--light-text-color);
     margin-bottom: 10px;


.experience-card .description 
    margin-top: 15px;
    line-height: 1.7;
    color: var(--text-color);


.education-card .major 
     margin-top: 10px;
     color: var(--text-color);
     line-height: 1.6;


/* Skills Section */
.skills-grid 
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 30px;


.skill-category ul 
    list-style: none;
    padding: 0;
    margin-top: 15px;


.skill-category li 
    margin-bottom: 8px;
    padding-left: 1.5em;
    position: relative;
    font-size: 1em;

.skill-category li::before 
    content: '\2022'; /* Bullet point or use an icon */
    color: var(--secondary-color);
    position: absolute;
    left: 0;
    font-weight: bold;


.skill-category .proficiency 
    font-style: italic;
    color: var(--light-text-color);
    margin-top: 5px;
    font-size: 0.95em;


/* Contact Section */
.contact-grid 
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 50px;
    align-items: start;


.contact-info p 
    margin-bottom: 15px;
    font-size: 1.1em;
    display: flex;
    align-items: center;


.contact-info i 
    font-size: 1.3em;
    margin-right: 12px;


.contact-form-container h3 
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 1.8em;


.form-group 
    margin-bottom: 20px;


.form-group label 
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--primary-color);


.form-group input[type="text"],
.form-group input[type="email"],
.form-group textarea 
    width: 100%;
    padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-family: var(--body-font);
    font-size: 1em;
    transition: border-color var(--transition-speed), box-shadow var(--transition-speed);


.form-group input[type="text"]:focus,
.form-group input[type="email"]:focus,
.form-group textarea:focus 
    border-color: var(--secondary-color);
    box-shadow: 0 0 5px rgba(95, 162, 224, 0.5); /* Match secondary color with some transparency */
    outline: none;


textarea 
    resize: vertical;


.form-status 
    margin-top: 20px;
    text-align: center;
    font-weight: 600;


/* Footer */
footer 
    background: var(--primary-color);
    color: #fff;
    padding: 30px 0;
    text-align: center;
    font-size: 0.9em;


footer .container 
    display: flex;
    flex-direction: column;
    align-items: center;


.social-links 
    margin-top: 15px;


.social-links a 
    color: #fff;
    font-size: 1.5em;
    margin: 0 10px;
    transition: color var(--transition-speed);


.social-links a:hover 
    color: var(--secondary-color);


/* Animations & Effects (Subtle) */
@keyframes fadeInUp 
    from 
        opacity: 0;
        transform: translateY(20px);
    
    to 
        opacity: 1;
        transform: translateY(0);
    


.section h2,
.section .section-description,
.about-content,
.experience-grid,
.education-grid,
.skills-grid,
.contact-grid 
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease-out, transform 0.6s ease-out;


.section.is-visible h2,
.section.is-visible .section-description,
.section.is-visible .about-content,
.section.is-visible .experience-grid,
.section.is-visible .education-grid,
.section.is-visible .skills-grid,
.section.is-visible .contact-grid 
    opacity: 1;
    transform: translateY(0);


/* Stagger animation for cards */
.section.is-visible .card 
    animation: fadeInUp 0.6s ease-out backwards;
    /* Delay will be applied via JS */


/* Responsiveness */
@media (max-width: 768px) 
    h1 
        font-size: 2.5em;
    
    h2 
        font-size: 2em;
    
    section 
        padding: 60px 0;
    

    /* Nav Toggle */
    .nav-toggle 
        display: block;
    

    nav 
        position: fixed;
        background: var(--primary-color);
        top: 0;
        right: 0;
        width: 70%; /* Adjust width as needed */
        max-width: 300px;
        height: 100%;
        padding: 80px 20px 20px;
        transform: translateX(100%);
        transition: transform var(--transition-speed);
        box-shadow: -4px 0 8px var(--shadow-color);
    

    nav ul 
        flex-direction: column;
    

    nav ul li 
        margin: 20px 0;
    

     nav ul li a 
         color: #fff;
         font-size: 1.2em;
     
      nav ul li a::after 
         background: #fff;
     

    .nav-open nav 
        transform: translateX(0);
    

    /* Hero Section */
    #hero .container 
        flex-direction: column;
        text-align: center;
    
    .hero-content h1 
         font-size: 3em;
    
    .hero-content .subtitle 
        font-size: 1.3em;
    

    .hero-graphic i 
        font-size: 6em;
         margin-top: 40px;
    
      .graphic-shape 
        width: 180px;
        height: 180px;
      

    /* Grids */
    .experience-grid, .education-grid, .skills-grid, .contact-grid 
        grid-template-columns: 1fr;
    

     .about-content 
         grid-template-columns: 1fr;
     
     .about-skills-summary 
         margin-top: 30px;
     

     .contact-form-container 
         order: -1; /* Move form above info on mobile */
     


/* Accessibility */
.nav-toggle[aria-expanded="true"] .hamburger 
    transform: rotate(45deg);


.nav-toggle[aria-expanded="true"] .hamburger::before 
    opacity: 0;


.nav-toggle[aria-expanded="true"] .hamburger::after 
    top: 0;
    transform: rotate(-90deg);
```
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
  
  
