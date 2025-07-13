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

    # Google Fonts CSS for default template (Cairo + Roboto)
    gf_default_path = "static/css/google-fonts-default.css"
    if not os.path.exists(gf_default_path):
        print("Downloading Google Fonts CSS for default template...")
        gf_url = "https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&family=Roboto:wght@300;400;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_default_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for default template
        download_font_files_from_css(gf_response.text, "default")
        print("✅ Google Fonts for default template downloaded")
    else:
        print("⏭️  Google Fonts for default template already exists, skipping...")

    # Google Fonts CSS for template1 (Roboto + Open Sans)
    gf_template1_path = "static/css/google-fonts-template1.css"
    if not os.path.exists(gf_template1_path):
        print("Downloading Google Fonts CSS for template1...")
        gf_url = "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&family=Open+Sans:wght@400;600;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_template1_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for template1
        download_font_files_from_css(gf_response.text, "template1")
        print("✅ Google Fonts for template1 downloaded")
    else:
        print("⏭️  Google Fonts for template1 already exists, skipping...")

    # Google Fonts CSS for modern theme (Lato + Roboto)
    gf_modern_path = "static/css/google-fonts-modern.css"
    if not os.path.exists(gf_modern_path):
        print("Downloading Google Fonts CSS for modern theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Roboto:wght@400;500;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_modern_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for modern theme
        download_font_files_from_css(gf_response.text, "modern")
        print("✅ Google Fonts for modern theme downloaded")
    else:
        print("⏭️  Google Fonts for modern theme already exists, skipping...")

    # Google Fonts CSS for classic theme (EB Garamond + Lato)
    gf_classic_path = "static/css/google-fonts-classic.css"
    if not os.path.exists(gf_classic_path):
        print("Downloading Google Fonts CSS for classic theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;700&family=Lato:wght@300;400;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_classic_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for classic theme
        download_font_files_from_css(gf_response.text, "classic")
        print("✅ Google Fonts for classic theme downloaded")
    else:
        print("⏭️  Google Fonts for classic theme already exists, skipping...")

    # Google Fonts CSS for creative theme (Poppins + Merriweather)
    gf_creative_path = "static/css/google-fonts-creative.css"
    if not os.path.exists(gf_creative_path):
        print("Downloading Google Fonts CSS for creative theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Merriweather:wght@400;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_creative_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for creative theme
        download_font_files_from_css(gf_response.text, "creative")
        print("✅ Google Fonts for creative theme downloaded")
    else:
        print("⏭️  Google Fonts for creative theme already exists, skipping...")

    # Google Fonts CSS for tech theme (Roboto Mono + VT323)
    gf_tech_path = "static/css/google-fonts-tech.css"
    if not os.path.exists(gf_tech_path):
        print("Downloading Google Fonts CSS for tech theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500&family=VT323&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_tech_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for tech theme
        download_font_files_from_css(gf_response.text, "tech")
        print("✅ Google Fonts for tech theme downloaded")
    else:
        print("⏭️  Google Fonts for tech theme already exists, skipping...")

    # Google Fonts CSS for modern gradient theme (Inter + Playfair Display)
    gf_modern_gradient_path = "static/css/google-fonts-modern-gradient.css"
    if not os.path.exists(gf_modern_gradient_path):
        print("Downloading Google Fonts CSS for modern gradient theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_modern_gradient_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for modern gradient theme
        download_font_files_from_css(gf_response.text, "modern_gradient")
        print("✅ Google Fonts for modern gradient theme downloaded")
    else:
        print("⏭️  Google Fonts for modern gradient theme already exists, skipping...")

    # Google Fonts CSS for minimal theme (Inter + Source Serif Pro)
    gf_minimal_path = "static/css/google-fonts-minimal.css"
    if not os.path.exists(gf_minimal_path):
        print("Downloading Google Fonts CSS for minimal theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+Pro:wght@400;600&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_minimal_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for minimal theme
        download_font_files_from_css(gf_response.text, "minimal")
        print("✅ Google Fonts for minimal theme downloaded")
    else:
        print("⏭️  Google Fonts for minimal theme already exists, skipping...")

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

    # Update Font Awesome CSS to use local fonts (only if CSS was downloaded)
    if os.path.exists(fa_css_path):
        with open(fa_css_path, "r", encoding="utf-8") as f:
            fa_css = f.read()

        if "../webfonts/" in fa_css:  # Only update if not already updated
            fa_css = fa_css.replace("../webfonts/", "../fonts/")
            with open(fa_css_path, "w", encoding="utf-8") as f:
                f.write(fa_css)
            print("✅ Font Awesome CSS updated to use local fonts")

    print("🎉 All assets downloaded successfully!")


def download_font_files_from_css(css_content, template_suffix):
    """Download font files referenced in Google Fonts CSS"""
    font_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css_content)

    for i, font_url in enumerate(font_urls):
        font_filename = f"font_{template_suffix}_{i+1}.woff2"
        font_path = f"static/fonts/{font_filename}"

        if not os.path.exists(font_path):
            print(
                f"  Downloading font file {i+1}/{len(font_urls)} for {template_suffix}..."
            )
            font_response = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(font_response.content)
        else:
            print(
                f"  ⏭️  Font file {i+1} for {template_suffix} already exists, skipping..."
            )

        # Update CSS to use local fonts
        css_file = f"static/css/google-fonts-{template_suffix}.css"
        with open(css_file, "r", encoding="utf-8") as f:
            css_content_updated = f.read()
        css_content_updated = css_content_updated.replace(
            font_url, f"../fonts/{font_filename}"
        )
        with open(css_file, "w", encoding="utf-8") as f:
            f.write(css_content_updated)


if __name__ == "__main__":
    download_assets()
