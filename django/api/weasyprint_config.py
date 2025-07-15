"""
WeasyPrint Performance Optimization Configuration

This module contains optimizations for faster PDF generation with WeasyPrint.
All new templates are designed with these optimizations in mind.
"""

# WeasyPrint optimization settings
WEASYPRINT_OPTIMIZATIONS = {
    # Disable unnecessary features for better performance
    'presentational_hints': False,
    'target_collector': None,
    
    # Optimize rendering
    'optimize_size': ['fonts', 'images'],
    
    # Use system fonts only (no external font loading)
    'font_config': None,
    
    # Reduce memory usage
    'unresolved_references': 'ignore',
    
    # Optimize for print
    'print_background': True,
}

# Font performance optimizations
SYSTEM_FONT_STACK = {
    'sans-serif': [
        '-apple-system',
        'BlinkMacSystemFont', 
        'Segoe UI',
        'Roboto',
        'Inter',
        'Helvetica Neue',
        'Arial',
        'sans-serif'
    ],
    'serif': [
        'Georgia',
        'Times New Roman', 
        'Times',
        'serif'
    ],
    'monospace': [
        'SF Mono',
        'Monaco',
        'Cascadia Code',
        'Roboto Mono',
        'Consolas',
        'Courier New',
        'monospace'
    ]
}

# CSS optimization rules
CSS_OPTIMIZATIONS = {
    # Avoid complex selectors
    'max_selector_depth': 3,
    
    # Use efficient properties
    'efficient_properties': [
        'margin', 'padding', 'font-family', 'font-size', 
        'font-weight', 'color', 'background-color',
        'border', 'border-radius', 'text-align'
    ],
    
    # Avoid expensive properties for print
    'avoid_properties': [
        'box-shadow', 'text-shadow', 'filter', 
        'backdrop-filter', 'transform', 'animation'
    ],
    
    # Use simple gradients only when necessary
    'simple_gradients_only': True,
    
    # Optimize images
    'image_optimization': {
        'max_width': 800,
        'max_height': 600,
        'quality': 85
    }
}

# Template performance guidelines
TEMPLATE_GUIDELINES = {
    'max_sections': 15,
    'max_items_per_section': 20,
    'recommended_font_sizes': {
        'h1': '2.5rem',
        'h2': '1.2rem', 
        'h3': '1.1rem',
        'body': '10pt'
    },
    'optimal_line_height': 1.6,
    'max_colors_per_theme': 6
}

def get_optimized_css_config():
    """Return CSS configuration optimized for WeasyPrint performance"""
    return {
        'font_family_primary': ', '.join(SYSTEM_FONT_STACK['sans-serif']),
        'font_family_serif': ', '.join(SYSTEM_FONT_STACK['serif']),
        'font_family_mono': ', '.join(SYSTEM_FONT_STACK['monospace']),
        'optimizations': CSS_OPTIMIZATIONS
    }

def get_weasyprint_config():
    """Return WeasyPrint configuration for optimal performance"""
    return WEASYPRINT_OPTIMIZATIONS
