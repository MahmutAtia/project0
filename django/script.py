import requests
import os
import re


def download_assets():
    """Download external fonts and icons for local use"""

    # Create directories if they don't exist
    os.makedirs("static/fonts", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)

    # Font Awesome CSS
    fa_css_path = "static/css/fontawesome.min.css"
    if not os.path.exists(fa_css_path):
        print("Downloading Font Awesome CSS...")
        fa_url = (
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
        )
        fa_response = requests.get(fa_url)
        with open(fa_css_path, "w", encoding="utf-8") as f:
            f.write(fa_response.text)
        print("✅ Font Awesome CSS downloaded")
    else:
        print("⏭️  Font Awesome CSS already exists, skipping...")

    # Font combinations for each template
    font_combinations = {
        'roboto-opensans': {
            'name': 'Roboto + Open Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Open+Sans:wght@300;400;600;700&display=swap'
        },
        'inter-sourcesans': {
            'name': 'Inter + Source Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Sans+Pro:wght@300;400;600;700&display=swap'
        },
        'lato-merriweather': {
            'name': 'Lato + Merriweather',
            'url': 'https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Merriweather:wght@400;700&display=swap'
        },
        'nunito-crimson': {
            'name': 'Nunito + Crimson Text',
            'url': 'https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&family=Crimson+Text:wght@400;600;700&display=swap'
        },
        'sourcesans-sourceserif': {
            'name': 'Source Sans Pro + Source Serif Pro',
            'url': 'https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&family=Source+Serif+Pro:wght@400;600;700&display=swap'
        },
        'calibri-times': {
            'name': 'Calibri + Times New Roman',
            'fallback': True,  # System fonts, no download needed
            'primary': 'Calibri, sans-serif',
            'secondary': '"Times New Roman", serif'
        },
        'arial-georgia': {
            'name': 'Arial + Georgia',
            'fallback': True,  # System fonts, no download needed
            'primary': 'Arial, sans-serif',
            'secondary': 'Georgia, serif'
        },
        'roboto-robotoslab': {
            'name': 'Roboto + Roboto Slab',
            'url': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Slab:wght@400;500;700&display=swap'
        },
        'inter-poppins': {
            'name': 'Inter + Poppins',
            'url': 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@300;400;500;600;700&display=swap'
        },
        'montserrat-sourcesans': {
            'name': 'Montserrat + Source Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&family=Source+Sans+Pro:wght@300;400;600;700&display=swap'
        },
        'nunitosans-opensans': {
            'name': 'Nunito Sans + Open Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700&family=Open+Sans:wght@300;400;600;700&display=swap'
        },
        'worksans-lora': {
            'name': 'Work Sans + Lora',
            'url': 'https://fonts.googleapis.com/css2?family=Work+Sans:wght@300;400;500;600;700&family=Lora:wght@400;500;700&display=swap'
        },
        'crimson-lato': {
            'name': 'Crimson Text + Lato',
            'url': 'https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600;700&family=Lato:wght@300;400;700&display=swap'
        },
        'playfair-sourcesans': {
            'name': 'Playfair Display + Source Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;700&family=Source+Sans+Pro:wght@300;400;600;700&display=swap'
        },
        'cormorant-lato': {
            'name': 'Cormorant + Lato',
            'url': 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;700&family=Lato:wght@300;400;700&display=swap'
        },
        'librebaskerville-opensans': {
            'name': 'Libre Baskerville + Open Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Open+Sans:wght@300;400;600;700&display=swap'
        },
        'nunitosans-sourceserif': {
            'name': 'Nunito Sans + Source Serif',
            'url': 'https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700&family=Source+Serif+Pro:wght@400;600&display=swap'
        },
        'system-georgia': {
            'name': 'System UI + Georgia',
            'fallback': True,  # System fonts, no download needed
            'primary': 'system-ui, sans-serif',
            'secondary': 'Georgia, serif'
        },
        'inter-charter': {
            'name': 'Inter + Charter',
            'url': 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
            'secondary_fallback': 'Charter, serif'  # Charter is system font on many systems
        },
        'karla-spectral': {
            'name': 'Karla + Spectral',
            'url': 'https://fonts.googleapis.com/css2?family=Karla:wght@300;400;500;700&family=Spectral:wght@400;500;700&display=swap'
        },
        'poppins-merriweather': {
            'name': 'Poppins + Merriweather',
            'url': 'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Merriweather:wght@400;700&display=swap'
        },
        'comfortaa-opensans': {
            'name': 'Comfortaa + Open Sans',
            'url': 'https://fonts.googleapis.com/css2?family=Comfortaa:wght@300;400;700&family=Open+Sans:wght@300;400;600;700&display=swap'
        },
        'raleway-lora': {
            'name': 'Raleway + Lora',
            'url': 'https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&family=Lora:wght@400;500;700&display=swap'
        },
        'quicksand-crimson': {
            'name': 'Quicksand + Crimson Text',
            'url': 'https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;700&family=Crimson+Text:wght@400;600;700&display=swap'
        },
        'ibmplexsans-ibmplexserif': {
            'name': 'IBM Plex Sans + IBM Plex Serif',
            'url': 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;700&family=IBM+Plex+Serif:wght@400;500;700&display=swap'
        }
    }

    # Download font combinations
    for font_key, font_config in font_combinations.items():
        if font_config.get('fallback'):
            print(f"⏭️  {font_config['name']} uses system fonts, skipping download...")
            continue
            
        css_path = f"static/css/fonts-{font_key}.css"
        if not os.path.exists(css_path):
            print(f"Downloading {font_config['name']} fonts...")
            response = requests.get(font_config['url'])
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            # Download font files
            download_font_files_from_css(response.text, font_key)
            print(f"✅ {font_config['name']} fonts downloaded")
        else:
            print(f"⏭️  {font_config['name']} fonts already exist, skipping...")

    # Download Font Awesome font files
    fa_fonts = ["fa-solid-900.woff2", "fa-brands-400.woff2", "fa-regular-400.woff2"]

    for font_file in fa_fonts:
        font_path = f"static/fonts/{font_file}"
        if not os.path.exists(font_path):
            print(f"Downloading {font_file}...")
            font_url = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/{font_file}"
            response = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(response.content)
            print(f"✅ {font_file} downloaded")
        else:
            print(f"⏭️  {font_file} already exists, skipping...")

    # Update Font Awesome CSS to use local fonts
    if os.path.exists(fa_css_path):
        with open(fa_css_path, "r", encoding="utf-8") as f:
            fa_css = f.read()

        if "../webfonts/" in fa_css:
            fa_css = fa_css.replace("../webfonts/", "../fonts/")
            with open(fa_css_path, "w", encoding="utf-8") as f:
                f.write(fa_css)
            print("✅ Font Awesome CSS updated to use local fonts")

    print("🎉 All assets downloaded successfully!")


def download_font_files_from_css(css_content, font_key):
    """Download font files referenced in Google Fonts CSS"""
    font_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css_content)

    for i, font_url in enumerate(font_urls):
        font_filename = f"font_{font_key}_{i+1}.woff2"
        font_path = f"static/fonts/{font_filename}"

        if not os.path.exists(font_path):
            print(f"  Downloading font file {i+1}/{len(font_urls)} for {font_key}...")
            font_response = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(font_response.content)
        else:
            print(f"  ⏭️  Font file {i+1} for {font_key} already exists, skipping...")

        # Update CSS to use local fonts
        css_file = f"static/css/fonts-{font_key}.css"
        with open(css_file, "r", encoding="utf-8") as f:
            css_content_updated = f.read()
        css_content_updated = css_content_updated.replace(
            font_url, f"../fonts/{font_filename}"
        )
        with open(css_file, "w", encoding="utf-8") as f:
            f.write(css_content_updated)


if __name__ == "__main__":
    download_assets()