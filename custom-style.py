"""
Custom styling for the Academic Information Hub application.
This can be modified separately from the main application logic.
"""

# Material Design color palette
PRIMARY = "#6200EE"
PRIMARY_VARIANT = "#3700B3" 
SECONDARY = "#03DAC6"
SECONDARY_VARIANT = "#018786"
BACKGROUND = "#FFFFFF"
SURFACE = "#FFFFFF"
ERROR = "#B00020"
ON_PRIMARY = "#FFFFFF"
ON_SECONDARY = "#000000"
ON_BACKGROUND = "#000000"
ON_SURFACE = "#000000"
ON_ERROR = "#FFFFFF"

# Additional colors
CARD_BG = "#FFFFFF"
SIDEBAR_BG = "#F0F0F5"
HOVER_BG = "#E8E8F0"
SELECTED_BG = "#E1D3F5"
BORDER_COLOR = "#E0E0E0"
TEXT_PRIMARY = "#333333"
TEXT_SECONDARY = "#666666"

# Get stylesheet for the application
def get_stylesheet():
    """Return the custom stylesheet for the application."""
    return f"""
        QMainWindow {{
            background-color: {BACKGROUND};
        }}
        
        .sidebar {{
            background-color: {SIDEBAR_BG};
            border-right: 1px solid {BORDER_COLOR};
        }}
        
        .content-area {{
            background-color: {SURFACE};
        }}
        
        .chat-area {{
            background-color: {BACKGROUND};
            border-top: 1px solid {BORDER_COLOR};
        }}
        
        .section-header {{
            font-size: 18px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 12px;
        }}
        
        .content-header {{
            font-size: 24px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 16px;
        }}
        
        .date-header {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 12px;
            text-align: left;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .class-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .filter-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 12px;
            text-align: center;
            color: {TEXT_PRIMARY};
        }}
        
        .filter-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .filter-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .activity-item {{
            background-color: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
            padding: 12px;
            margin: 6px 0;
        }}
        
        .activity-item:hover {{
            border-color: {PRIMARY_VARIANT};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .activity-title {{
            font-size: 15px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .activity-course {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
        }}
        
        .activity-status {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
            margin-left: 16px;
        }}
        
        .icon-button {{
            background-color: transparent;
            border: none;
            border-radius: 16px;
        }}
        
        .icon-button:hover {{
            background-color: rgba(0, 0, 0, 0.05);
        }}
        
        .separator {{
            color: {BORDER_COLOR};
        }}
        
        .chat-input {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 10px 16px;
            font-size: 14px;
            background-color: {SURFACE};
        }}
        
        .chat-display {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 16px;
            background-color: {SURFACE};
            font-size: 14px;
        }}
        
        .date-label {{
            font-size: 14px;
            color: {TEXT_SECONDARY};
            margin-bottom: 4px;
        }}
        
        .date-field {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 12px;
            background-color: {SURFACE};
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: {BACKGROUND};
            width: 8px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {BORDER_COLOR};
            border-radius: 4px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {BACKGROUND};
            height: 8px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {BORDER_COLOR};
            border-radius: 4px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """

# Get a material palette for qt-material library
def get_material_palette():
    """Return a palette configuration for qt-material library."""
    return {
        'primary': PRIMARY,
        'primaryLightColor': PRIMARY_VARIANT,
        'secondaryColor': SECONDARY,
        'secondaryLightColor': SECONDARY_VARIANT,
        'secondaryDarkColor': SECONDARY_VARIANT,
        'primaryTextColor': ON_PRIMARY,
        'secondaryTextColor': ON_SECONDARY
    }
