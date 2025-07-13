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

    # Google Fonts CSS for default template (Roboto + Open Sans - Professional & Clean)
    gf_default_path = "static/css/google-fonts-default.css"
    if not os.path.exists(gf_default_path):
        print("Downloading Google Fonts CSS for default template...")
        gf_url = "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Open+Sans:wght@300;400;600;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_default_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for default template
        download_font_files_from_css(gf_response.text, "default")
        print("✅ Google Fonts for default template downloaded")
    else:
        print("⏭️  Google Fonts for default template already exists, skipping...")

    # Google Fonts CSS for europass template (Source Sans Pro + Source Serif Pro - Official EU Style)
    gf_europass_path = "static/css/google-fonts-europass.css"
    if not os.path.exists(gf_europass_path):
        print("Downloading Google Fonts CSS for europass template...")
        gf_url = "https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&family=Source+Serif+Pro:wght@400;600;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_europass_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for europass template
        download_font_files_from_css(gf_response.text, "europass")
        print("✅ Google Fonts for europass template downloaded")
    else:
        print("⏭️  Google Fonts for europass template already exists, skipping...")

    # Google Fonts CSS for modern theme (Inter + DM Sans - Contemporary & Readable)
    gf_modern_path = "static/css/google-fonts-modern.css"
    if not os.path.exists(gf_modern_path):
        print("Downloading Google Fonts CSS for modern theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_modern_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for modern theme
        download_font_files_from_css(gf_response.text, "modern")
        print("✅ Google Fonts for modern theme downloaded")
    else:
        print("⏭️  Google Fonts for modern theme already exists, skipping...")

    # Google Fonts CSS for classic theme (Crimson Text + Lato - Elegant & Timeless)
    gf_classic_path = "static/css/google-fonts-classic.css"
    if not os.path.exists(gf_classic_path):
        print("Downloading Google Fonts CSS for classic theme...")
        gf_url = "https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600;700&family=Lato:wght@300;400;700&display=swap"
        gf_response = requests.get(gf_url)
        with open(gf_classic_path, "w", encoding="utf-8") as f:
            f.write(gf_response.text)

        # Download font files for classic theme
        download_font_files_from_css(gf_response.text, "classic")
        print("✅ Google Fonts for classic theme downloaded")
    else:
        print("⏭️  Google Fonts for classic theme already exists, skipping...")


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
