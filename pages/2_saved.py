"""
"Saved" page: a persistent track record of perfumes, notes, and accords
you've saved over time, kept on disk (data/saved_history.json) so it
survives restarting the app.

Perfumes are saved from home.py in one of two ways, each producing a
different tag:
  - "liked": saved via the "Save current selection" button, for perfumes
    you searched and picked yourself.
  - "recommended": saved via the "Save this recommendation" button on an
    individual recommendation card.

Saving a perfume (either way) automatically adds its notes and accords to
two separate, deduplicated lists, incrementing a count each time (used
later for a "most common note/accord" scorecard). Removing a perfume,
note, or accord here always deletes that entry completely; the three
lists are independent once populated, removing one never cascades to the
others.
"""

import streamlit as st

from constants import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BACKGROUND_DARK,
    BACKGROUND_LIGHT,
    CARD_BACKGROUND,
    CARD_TEXT_PRIMARY,
    CARD_TEXT_SECONDARY,
    CHIP_BACKGROUND,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from saved_history import (
    load_saved_history,
    remove_accord_from_history,
    remove_note_from_history,
    remove_perfume_from_history,
    save_history_to_disk,
)

st.set_page_config(page_title="Saved", layout="wide")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_LIGHT};
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stHeader"] {{
        background-color: transparent;
    }}
    [data-testid="stHeader"] * {{
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stToolbar"] {{
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stSidebar"] {{
        background-color: {BACKGROUND_DARK};
    }}
    [data-testid="stSidebar"] * {{
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stCaptionContainer"] {{
        color: {TEXT_SECONDARY};
    }}
    .stButton > button {{
        background-color: {ACCENT_PRIMARY};
        color: {CARD_TEXT_PRIMARY};
        border: none;
    }}
    .stButton > button:hover {{
        background-color: {ACCENT_HOVER};
        color: {CARD_TEXT_PRIMARY};
    }}
    [class*="st-key-remove-perfume-"] [data-testid="stBaseButton-secondary"],
    [class*="st-key-remove-note-"] [data-testid="stBaseButton-secondary"],
    [class*="st-key-remove-accord-"] [data-testid="stBaseButton-secondary"] {{
        width: 1.25rem !important;
        height: 1.25rem !important;
        max-width: 1.25rem !important;
        min-width: 1.25rem !important;
        padding: 0 !important;
        line-height: 1;
        font-size: 0.8rem;
        border-radius: 4px !important;
        box-sizing: border-box;
    }}
    [class*="st-key-saved-perfume-"] {{
        background-color: {CARD_BACKGROUND} !important;
        border: 1px solid {CARD_TEXT_SECONDARY} !important;
        border-radius: 8px;
    }}
    [class*="st-key-saved-perfume-"] p,
    [class*="st-key-saved-perfume-"] span {{
        color: {CARD_TEXT_PRIMARY} !important;
    }}
    [class*="st-key-saved-perfume-"] [data-testid="stCaptionContainer"] {{
        color: {CARD_TEXT_SECONDARY} !important;
    }}
    .saved-chip {{
        background-color: {CHIP_BACKGROUND};
        color: {TEXT_PRIMARY};
        border-radius: 6px;
        padding: 6px 10px;
        margin-bottom: 6px;
        font-size: 14px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Saved")
st.caption("Perfumes, notes, and accords you've saved. This persists across restarts.")


def format_tier_notes(notes_list):
    """Render a tier's note list as a comma-separated string, matching
    home.py's own format_notes so the wording is consistent across pages.
    """
    if not notes_list:
        return "none recorded"
    return ", ".join(notes_list)


def render_note_breakdown(perfume):
    """Render the note breakdown for a saved perfume card. Prefers the
    top/heart/base tier split, but some perfumes in the dataset never had
    their notes categorised into pyramid tiers (all three tier lists are
    empty even though all_notes has real data) -- for those, three empty
    "none recorded" lines would be actively unhelpful. When every tier is
    empty but all_notes isn't, falls back to a single flat "Notes: ..."
    line instead. Matches home.py's own render_note_breakdown so the two
    pages behave consistently.
    """
    top_notes = perfume.get("top_notes", [])
    mid_notes = perfume.get("mid_notes", [])
    base_notes = perfume.get("base_notes", [])
    has_tier_data = bool(top_notes) or bool(mid_notes) or bool(base_notes)
    if has_tier_data:
        st.caption(f"Top notes: {format_tier_notes(top_notes)}")
        st.caption(f"Heart notes: {format_tier_notes(mid_notes)}")
        st.caption(f"Base notes: {format_tier_notes(base_notes)}")
    else:
        st.caption(f"Notes: {format_tier_notes(perfume.get('all_notes', []))}")


history = load_saved_history()

liked_perfumes = [(i, p) for i, p in enumerate(history["perfumes"]) if p["tag"] == "liked"]
recommended_perfumes = [(i, p) for i, p in enumerate(history["perfumes"]) if p["tag"] == "recommended"]

st.markdown("## Perfumes")

if not history["perfumes"]:
    st.markdown(
        "<div style='text-align: left;'>Nothing saved yet. Use "
        "<strong>Save current selection</strong> or "
        "<strong>Save this recommendation</strong> on the home page.</div>",
        unsafe_allow_html=True,
    )
else:
    perfume_col_liked, perfume_col_recommended = st.columns(2)

    with perfume_col_liked:
        st.markdown("### Liked")
        if not liked_perfumes:
            st.caption("None saved yet.")
        for index, perfume in liked_perfumes:
            with st.container(border=True, key=f"saved-perfume-liked-{index}"):
                year_str = f", {int(perfume['year'])}" if perfume["year"] else ""
                header_cols = st.columns([4, 1])
                with header_cols[0]:
                    st.markdown(f"**{perfume['name']}** ({perfume['brand']}{year_str})")
                with header_cols[1]:
                    if st.button("✕", key=f"remove-perfume-{index}"):
                        remove_perfume_from_history(history, index)
                        save_history_to_disk(history)
                        st.rerun()
                render_note_breakdown(perfume)
                st.caption(
                    f"Accords: {', '.join(perfume['accords'].keys()) if perfume['accords'] else 'none recorded'}"
                )

    with perfume_col_recommended:
        st.markdown("### Recommended")
        if not recommended_perfumes:
            st.caption("None saved yet.")
        for index, perfume in recommended_perfumes:
            with st.container(border=True, key=f"saved-perfume-recommended-{index}"):
                year_str = f", {int(perfume['year'])}" if perfume["year"] else ""
                header_cols = st.columns([4, 1])
                with header_cols[0]:
                    st.markdown(f"**{perfume['name']}** ({perfume['brand']}{year_str})")
                with header_cols[1]:
                    if st.button("✕", key=f"remove-perfume-{index}-r"):
                        remove_perfume_from_history(history, index)
                        save_history_to_disk(history)
                        st.rerun()
                render_note_breakdown(perfume)
                st.caption(
                    f"Accords: {', '.join(perfume['accords'].keys()) if perfume['accords'] else 'none recorded'}"
                )

st.markdown("## Notes")
if not history["notes"]:
    st.caption("No notes saved yet.")
else:
    for note_name in sorted(history["notes"].keys()):
        chip_cols = st.columns([8, 1])
        chip_cols[0].markdown(f'<div class="saved-chip">{note_name}</div>', unsafe_allow_html=True)
        if chip_cols[1].button("✕", key=f"remove-note-{note_name}"):
            remove_note_from_history(history, note_name)
            save_history_to_disk(history)
            st.rerun()

st.markdown("## Accords")
if not history["accords"]:
    st.caption("No accords saved yet.")
else:
    for accord_name in sorted(history["accords"].keys()):
        chip_cols = st.columns([8, 1])
        chip_cols[0].markdown(f'<div class="saved-chip">{accord_name}</div>', unsafe_allow_html=True)
        if chip_cols[1].button("✕", key=f"remove-accord-{accord_name}"):
            remove_accord_from_history(history, accord_name)
            save_history_to_disk(history)
            st.rerun()
