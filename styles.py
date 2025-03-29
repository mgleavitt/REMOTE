"""
Style definitions for the REMOTE application.
"""
import os

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
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 8px;
        }}
        
        .content-header {{
            font-size: 20px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin: 0;
            padding: 0;
            line-height: 28px;  /* Match the height of the date widgets */
        }}
        
        .date-header {{
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 10px;
            text-align: left;
            color: {TEXT_PRIMARY};
            margin-bottom: 4px;
        }}
        
        .class-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .class-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .filter-group {{
            margin-top: 8px;
            margin-bottom: 8px;
        }}
        
        .filter-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 10px;
            text-align: left;
            color: {TEXT_PRIMARY};
            margin-bottom: 4px;
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
            border-radius: 6px;
            padding: 8px;
            margin: 2px 0;
        }}
        
        .activity-item:hover {{
            border-color: {PRIMARY_VARIANT};
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .activity-title {{
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .activity-course {{
            font-size: 12px;
            color: {TEXT_SECONDARY};
        }}
        
        .activity-status {{
            font-size: 12px;
            color: {TEXT_SECONDARY};
            margin-left: 12px;
        }}
        
        .icon-button {{
            background-color: transparent;
            border: none;
            border-radius: 16px;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
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
            padding: 8px 12px;
            font-size: 13px;
            background-color: {SURFACE};
        }}
        
        .chat-display {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 12px;
            background-color: {SURFACE};
            font-size: 13px;
        }}
        
        .date-label {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
            margin: 0;
            padding: 0;
            line-height: 28px;  /* Match the height of the date widgets */
        }}
        
        .date-field {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            background-color: {SURFACE};
            margin: 0;
        }}
        
        QDateEdit {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            background-color: {SURFACE};
            color: {TEXT_PRIMARY};
        }}
        
        QDateEdit::drop-down {{
            border: none;
            width: 20px;
            subcontrol-origin: padding;
            subcontrol-position: center right;
            image: url({os.path.join(os.path.dirname(__file__), "icons", "calendar.svg")});
        }}
        
        QDateEdit::down-arrow {{
            image: url({os.path.join(os.path.dirname(__file__), "icons", "calendar.svg")});
            width: 16px;
            height: 16px;
        }}
        
        QCalendarWidget {{
            color: {TEXT_PRIMARY};
        }}
        
        QCalendarWidget QAbstractItemView {{
            color: {TEXT_PRIMARY};
            background-color: {SURFACE};
            selection-background-color: {SELECTED_BG};
            selection-color: {TEXT_PRIMARY};
        }}
        
        QGroupBox {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            margin-top: 14px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 3px;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: {BACKGROUND};
            width: 6px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {BORDER_COLOR};
            border-radius: 3px;
            min-height: 20px;
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
            height: 6px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {BORDER_COLOR};
            border-radius: 3px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        .chat-message {{
            background-color: {SURFACE};
            border: 1px solid {BORDER_COLOR};
            border-radius: 12px;
            padding: 8px 12px;
            margin: 4px 0;
            color: {TEXT_PRIMARY};
        }}
        
        .chat-message-user {{
            background-color: {SELECTED_BG};
            border: 1px solid {PRIMARY};
            border-radius: 12px;
            padding: 8px 12px;
            margin: 4px 0;
            text-align: right;
            color: {TEXT_PRIMARY};
        }}
        
        .chat-message * {{
            color: {TEXT_PRIMARY};
        }}
        
        .chat-header {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 6px;
        }}
        .send-button {{
            background-color: {PRIMARY};
            color: {ON_PRIMARY};
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
        }}

        .send-button:hover {{
            background-color: {PRIMARY_VARIANT};
        }}

        .send-button:pressed {{
            background-color: {SECONDARY_VARIANT};
        }}    
    """