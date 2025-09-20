import time
import logging

# handle files import
from PyPDF2 import PdfReader
from docx import Document
from pdf2docx import Converter
import tempfile
import os
import io


import re
import json
from django.conf import settings
from django.template.loader import get_template, render_to_string
from django.template import Context
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from collections import OrderedDict

import random
import string
from django.utils.text import slugify
from .models import GeneratedWebsite

# from weasyprint.fonts import FontConfiguration # Optional - Not used, so removed

logger = logging.getLogger(__name__)


def generate_website_slug(user, resume_id):
    """
    Generate a unique website slug based on user's name and resume ID.
    Format: firstname-lastname-resume-{resume_id}[-{random}]
    """
    # Get user's first and last name
    first_name = user.first_name.strip() if user.first_name else ""
    last_name = user.last_name.strip() if user.last_name else ""
    
    # Fallback to username if no first/last name
    if not first_name and not last_name:
        base_name = user.username
    else:
        base_name = f"{first_name} {last_name}".strip()
    
    # Create base slug
    base_slug = slugify(base_name)


    
    # Check if this slug already exists
    original_slug = base_slug

    if not GeneratedWebsite.objects.filter(unique_id=base_slug).exists():
        return base_slug

    # If it exists, append resume ID
    base_slug = f"{base_slug}-{resume_id}"
    if not GeneratedWebsite.objects.filter(unique_id=base_slug).exists():
        return base_slug
    # If it still exists, append a random suffix
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    base_slug = f"{base_slug}-{random_suffix}"

    return base_slug


def generate_pdf_from_resume_data(
    resume_data, 
    template_theme, 
    chosen_theme,
    sections_sort=None,
    hidden_sections=None,
    scale="medium",
    show_icons=False,
    show_avatar=False,
    font_family=None,  
    is_document=False  # New parameter to indicate if generating for document
):
   
    """
    Generates a PDF from resume data using a universal Jinja2 template.
    Optimized for fast WeasyPrint rendering with system fonts and efficient CSS.

    Args:
        resume_data (dict): The resume data as a dictionary.
        template_theme (str, optional): The name of the HTML template file, used to determine style and layout.
            Defaults to 'resume_template_2.html'.
        chosen_theme (str, optional): The name of the CSS theme to apply.
            Defaults to 'theme-default'.
        sections_sort (list, optional): List of section keys in the desired order.
            If None, uses default order from template.
        hidden_sections (list, optional): List of section keys to hide.
            If None, no sections are hidden.
        scale (str, optional): Font scale - "small", "medium", or "large".
            Defaults to "medium".
        show_icons (bool, optional): Whether to show icons in section headers.
            Defaults to False.
        show_avatar (bool, optional): Whether to show avatar in the resume.
            Defaults to False.
        font_family (str, optional): Font family combination to use.
            Defaults to template's default font.

    Returns:
        bytes: The PDF file content as bytes. Returns None on error.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Use Jinja2 for all templates with optimized configuration
        templates_dir = os.path.join(base_dir, "html_templates")
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            # Optimize Jinja2 for performance
            cache_size=400,
            auto_reload=False,
        )
        
        # Get template configuration based on the selected theme
        template_config = get_template_config(template_theme)
        
        # All our templates now use the universal system
        template = None
        if is_document:
            template = env.get_template(template_theme)
        else:
            template = env.get_template('universal_template.html')


        # Map scale to CSS class
        scale_class_map = {
            "small": "font-size-small",
            "medium": "",  # Default, no class needed
            "large": "font-size-large"
        }
        scale_class = scale_class_map.get(scale, "")
        
        # Get font configuration
        font_config = get_font_config(font_family, template_config.get('template_style', 'default'))
        
        # Prepare template context with optimization flags
        template_context = {
            "theme_class": chosen_theme,
            "scale_class": scale_class,
            "show_icons": show_icons,
            'show_avatar': show_avatar,
            "font_family": font_config['css_name'],  # Add font family to context
            "font_css_file": font_config['css_file'],  # Add font CSS file to context

            "style": template_config.get('template_style', 'default'),
            "layout": template_config.get('layout_type', 'single_column'),
            "optimize_for_print": True,  # Flag for print optimizations
            **resume_data
        }
        
        # If sections_sort is provided, add it to the template context
        if sections_sort:
            template_context["sections_sort"] = sections_sort
            
        # If hidden_sections is provided, add it to the template context
        if hidden_sections:
            template_context["hidden_sections"] = hidden_sections
        
        html_out = template.render(**template_context)
        
        # Create HTML object with optimized settings for WeasyPrint performance
        html_obj = HTML(
            string=html_out, 
            base_url=base_dir,
            # Optimizations for faster rendering
            encoding='utf-8'
        )
        
        # Generate PDF with performance optimizations
        pdf_file = html_obj.write_pdf(
            # Optimize for smaller file size and faster generation
            optimize_images=True,
            presentational_hints=False,
            unresolved_references='ignore'
        )

        return pdf_file
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_font_config(font_family, template_style):
    """
    Returns font configuration based on font family selection.
    
    Args:
        font_family (str): The font family key (e.g., 'roboto-opensans')
        template_style (str): The template style to get default font if none specified
        
    Returns:
        dict: Font configuration with CSS class name and file path
    """
    
    # Font family configurations
    font_configs = {
        'roboto-opensans': {
            'css_name': 'roboto-opensans',
            'css_file': 'fonts-roboto-opensans.css',
            'primary': 'Roboto',
            'secondary': 'Open Sans'
        },
        'inter-sourcesans': {
            'css_name': 'inter-sourcesans',
            'css_file': 'fonts-inter-sourcesans.css',
            'primary': 'Inter',
            'secondary': 'Source Sans Pro'
        },
        'lato-merriweather': {
            'css_name': 'lato-merriweather',
            'css_file': 'fonts-lato-merriweather.css',
            'primary': 'Lato',
            'secondary': 'Merriweather'
        },
        'nunito-crimson': {
            'css_name': 'nunito-crimson',
            'css_file': 'fonts-nunito-crimson.css',
            'primary': 'Nunito',
            'secondary': 'Crimson Text'
        },
        'sourcesans-sourceserif': {
            'css_name': 'sourcesans-sourceserif',
            'css_file': 'fonts-sourcesans-sourceserif.css',
            'primary': 'Source Sans Pro',
            'secondary': 'Source Serif Pro'
        },
        'calibri-times': {
            'css_name': 'calibri-times',
            'css_file': None,  # System fonts
            'primary': 'Calibri',
            'secondary': 'Times New Roman'
        },
        'arial-georgia': {
            'css_name': 'arial-georgia',
            'css_file': None,  # System fonts
            'primary': 'Arial',
            'secondary': 'Georgia'
        },
        'roboto-robotoslab': {
            'css_name': 'roboto-robotoslab',
            'css_file': 'fonts-roboto-robotoslab.css',
            'primary': 'Roboto',
            'secondary': 'Roboto Slab'
        },
        'inter-poppins': {
            'css_name': 'inter-poppins',
            'css_file': 'fonts-inter-poppins.css',
            'primary': 'Inter',
            'secondary': 'Poppins'
        },
        'montserrat-sourcesans': {
            'css_name': 'montserrat-sourcesans',
            'css_file': 'fonts-montserrat-sourcesans.css',
            'primary': 'Montserrat',
            'secondary': 'Source Sans Pro'
        },
        'nunitosans-opensans': {
            'css_name': 'nunitosans-opensans',
            'css_file': 'fonts-nunitosans-opensans.css',
            'primary': 'Nunito Sans',
            'secondary': 'Open Sans'
        },
        'worksans-lora': {
            'css_name': 'worksans-lora',
            'css_file': 'fonts-worksans-lora.css',
            'primary': 'Work Sans',
            'secondary': 'Lora'
        },
        'crimson-lato': {
            'css_name': 'crimson-lato',
            'css_file': 'fonts-crimson-lato.css',
            'primary': 'Crimson Text',
            'secondary': 'Lato'
        },
        'playfair-sourcesans': {
            'css_name': 'playfair-sourcesans',
            'css_file': 'fonts-playfair-sourcesans.css',
            'primary': 'Playfair Display',
            'secondary': 'Source Sans Pro'
        },
        'cormorant-lato': {
            'css_name': 'cormorant-lato',
            'css_file': 'fonts-cormorant-lato.css',
            'primary': 'Cormorant Garamond',
            'secondary': 'Lato'
        },
        'librebaskerville-opensans': {
            'css_name': 'librebaskerville-opensans',
            'css_file': 'fonts-librebaskerville-opensans.css',
            'primary': 'Libre Baskerville',
            'secondary': 'Open Sans'
        },
        'nunitosans-sourceserif': {
            'css_name': 'nunitosans-sourceserif',
            'css_file': 'fonts-nunitosans-sourceserif.css',
            'primary': 'Nunito Sans',
            'secondary': 'Source Serif Pro'
        },
        'system-georgia': {
            'css_name': 'system-georgia',
            'css_file': None,  # System fonts
            'primary': 'system-ui',
            'secondary': 'Georgia'
        },
        'inter-charter': {
            'css_name': 'inter-charter',
            'css_file': 'fonts-inter-charter.css',
            'primary': 'Inter',
            'secondary': 'Charter'
        },
        'karla-spectral': {
            'css_name': 'karla-spectral',
            'css_file': 'fonts-karla-spectral.css',
            'primary': 'Karla',
            'secondary': 'Spectral'
        },
        'poppins-merriweather': {
            'css_name': 'poppins-merriweather',
            'css_file': 'fonts-poppins-merriweather.css',
            'primary': 'Poppins',
            'secondary': 'Merriweather'
        },
        'comfortaa-opensans': {
            'css_name': 'comfortaa-opensans',
            'css_file': 'fonts-comfortaa-opensans.css',
            'primary': 'Comfortaa',
            'secondary': 'Open Sans'
        },
        'raleway-lora': {
            'css_name': 'raleway-lora',
            'css_file': 'fonts-raleway-lora.css',
            'primary': 'Raleway',
            'secondary': 'Lora'
        },
        'quicksand-crimson': {
            'css_name': 'quicksand-crimson',
            'css_file': 'fonts-quicksand-crimson.css',
            'primary': 'Quicksand',
            'secondary': 'Crimson Text'
        },
        'ibmplexsans-ibmplexserif': {
            'css_name': 'ibmplexsans-ibmplexserif',
            'css_file': 'fonts-ibmplexsans-ibmplexserif.css',
            'primary': 'IBM Plex Sans',
            'secondary': 'IBM Plex Serif'
        }
    }
    
    # Default fonts for each template style
    template_defaults = {
        'default': 'roboto-opensans',
        'europass': 'sourcesans-sourceserif',
        'modern': 'inter-poppins',
        'classic': 'crimson-lato',
        'minimal': 'nunitosans-sourceserif',
        'creative': 'poppins-merriweather',
        'professional': 'inter-poppins'
    }
    
    # Use provided font_family or fall back to template default
    if not font_family:
        font_family = template_defaults.get(template_style, 'roboto-opensans')
    
    return font_configs.get(font_family, font_configs['roboto-opensans'])
def generate_html_from_yaml(json_data, template_name="html_bloks_template.html"):
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
            loader=FileSystemLoader("./html_templates/"),
            autoescape=select_autoescape(["html", "xml"]),  # Auto-escape HTML
        )
        template = env.get_template(template_name)

        # 4. Render the Jinja template with the data
        html_output = template.render(data=json_data)  # Pass the entire data dictionary

        return html_output

    except Exception as e:
        print(f"Error generating HTML: {e}")
        return None






def convert_pdf_to_docx(pdf_content, output_path=None):
    """
    Converts PDF content to DOCX format.

    Args:
        pdf_content (bytes): The PDF content as bytes
        output_path (str, optional): Path to save the output DOCX. If None, only the BytesIO object is returned.

    Returns:
        BytesIO: A BytesIO object containing the DOCX content
    """
    try:
        # Create temporary files for the conversion process
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_temp:
            pdf_temp.write(pdf_content)
            pdf_temp_path = pdf_temp.name

        docx_temp_path = pdf_temp_path.replace(".pdf", ".docx")

        # Convert PDF to DOCX
        cv = Converter(pdf_temp_path)
        cv.convert(docx_temp_path)
        cv.close()

        # Read the DOCX file into memory
        with open(docx_temp_path, "rb") as docx_file:
            docx_content = io.BytesIO(docx_file.read())

        # Optionally save the DOCX to the specified output path
        if output_path:
            with open(output_path, "wb") as f:
                f.write(docx_content.getvalue())

        # Clean up temporary files
        os.unlink(pdf_temp_path)
        os.unlink(docx_temp_path)

        docx_content.seek(0)
        return docx_content

    except Exception as e:
        print(f"Error converting PDF to DOCX: {e}")
        return None


def generate_docx_from_template(
    resume_data, template_theme="resume_template_2.html", chosen_theme="theme-default", sections_sort=None, hidden_sections=None
):
    """
    Generates a DOCX document from template data using WeasyPrint to PDF and then converting to DOCX.

    Args:
        resume_data (dict): The document data as a dictionary
        template_theme (str): The HTML template to use
        chosen_theme (str): CSS theme class name
        sections_sort (list, optional): List of section keys in the desired order
        hidden_sections (list, optional): List of section keys to hide

    Returns:
        BytesIO: The DOCX file content as BytesIO object. Returns None on error.
    """
    try:
        # First generate PDF using existing function
        pdf_content = generate_pdf_from_resume_data(
            resume_data, template_theme, chosen_theme, sections_sort, hidden_sections, is_document=True  # Indicate this is for a document
        )

        if pdf_content:
            # Convert PDF to DOCX
            docx_content = convert_pdf_to_docx(pdf_content)
            return docx_content
        return None
    except Exception as e:
        print(f"Error generating DOCX: {e}")
        return None


def get_template_config(template_name):
    """
    Returns template configuration based on template name.
    
    Args:
        template_name (str): Name of the template file
        
    Returns:
        dict: Configuration dictionary with template_style and layout_type
    """
    template_configs = {


        'default': {
            'template_style': 'default',
            'layout_type': 'single_column',
            'use_universal': True
        },
        'template1': {
            'template_style': 'europass',
            'layout_type': 'europass',
            'use_universal': True
        },
        'template2': {
            'template_style': 'modern',
            'layout_type': 'single_column',
            'use_universal': True
        },
        'template3': {
            'template_style': 'classic',
            'layout_type': 'single_column',
            'use_universal': True
        },
        'template4': {
            'template_style': 'minimal',
            'layout_type': 'single_column',
            'use_universal': True
        },
        'template5': {
            'template_style': 'creative',
            'layout_type': 'two_column',
            'use_universal': True
        },
    
        'professional': {
            'template_style': 'professional',
            'layout_type': 'single_column',
            'use_universal': True
        }
        

    }
    
    return template_configs.get(template_name, {
        'template_style': 'default',
        'layout_type': 'single_column',
        'use_universal': False
    })





