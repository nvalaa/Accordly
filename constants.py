"""
Shared constants for the config6 Streamlit app: colour palette and any other
project-wide preferences. Import from here rather than hardcoding values in
home.py or prep_data.py, so a palette or config change only needs editing
once.
"""

# ---------------------------------------------------------------------------
# Colour palette (10-colour master palette, plus derived additions)
# ---------------------------------------------------------------------------

# Light & surface tones (backgrounds & cards)
COLOUR_COOL_FROST = "#F6F7F8"      # light text / secondary background
COLOUR_SUPER_WHITE = "#F9FAFB"     # unused since the dark-page redesign; kept for reference
COLOUR_VAPOR = "#E0E4E7"           # secondary text on dark background

# Mid-tones (borders, secondary UI & icons)
COLOUR_SILVER_FROST = "#D1D5DB"    # card background, button (accent)
COLOUR_POLISHED_SLATE = "#8B959A"  # unused since the dark-page redesign; kept for reference
COLOUR_SHALE_GRAY = "#BCC5C9"      # button hover

# Dark accents (primary actions & branding)
COLOUR_RIVER_MOSS = "#44555A"    # primary text on cards
COLOUR_JUNIPER_BARK = "#526065"    # main page background

# Dark extremes (text & dark mode)
COLOUR_MIDNIGHT_ORE = "#2B3538"    # unused since the dark-page redesign; kept for reference
COLOUR_VOLCANIC_STONE = "#1F2729"  # dark mode canvas

# Derived additions, not in the original 10-colour palette
COLOUR_SLATE_MIST = "#7C888C"      # muted variant of River moss, secondary text on cards
COLOUR_WET_SLATE = "#3D4A4E"       # picked-item chip background

# Quick-mapping aliases. Prefer these role-based names in app code; the
# COLOUR_* constants above exist mainly as the named reference point back
# to the palette itself.
BACKGROUND_LIGHT = COLOUR_JUNIPER_BARK
CARD_BACKGROUND = COLOUR_SILVER_FROST
BORDER_SUBTLE = COLOUR_VAPOR
BORDER_MUTED = COLOUR_SILVER_FROST
TEXT_PRIMARY = COLOUR_COOL_FROST
TEXT_SECONDARY = COLOUR_VAPOR
CARD_TEXT_PRIMARY = COLOUR_RIVER_MOSS
CARD_TEXT_SECONDARY = COLOUR_SLATE_MIST
CHIP_BACKGROUND = COLOUR_WET_SLATE
CHIP_SECONDARY = COLOUR_SHALE_GRAY
ACCENT_PRIMARY = COLOUR_SILVER_FROST
ACCENT_HOVER = COLOUR_SHALE_GRAY
BACKGROUND_DARK = COLOUR_VOLCANIC_STONE


# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

DATA_DIR = "data"
CONFIG6_OBJECTS_PATH = f"{DATA_DIR}/config6_objects.pkl"

BLEND_RATIO = 0.5
DUPE_THRESHOLD = 0.80
