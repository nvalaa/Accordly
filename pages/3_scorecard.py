"""
"Scorecard" page: a simple summary of the most common notes and accords
across everything saved in the "Saved" page (liked and recommended
perfumes combined, since notes/accords counts don't distinguish tag).

Reads the same persistent data/saved_history.json that pages/2_saved.py
manages. This page is read-only, no editing/removal happens here.
"""

import streamlit as st

from constants import (
    BACKGROUND_DARK,
    BACKGROUND_LIGHT,
    CARD_BACKGROUND,
    CARD_TEXT_PRIMARY,
    CARD_TEXT_SECONDARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from saved_history import load_saved_history, most_common_per_tier

TOP_N = 10
TIER_MAX_RANKS = 3

st.set_page_config(page_title="Scorecard", layout="wide")

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
    [class*="st-key-scorecard-"] {{
        background-color: {CARD_BACKGROUND} !important;
        border: 1px solid {CARD_TEXT_SECONDARY} !important;
        border-radius: 8px;
    }}
    [class*="st-key-scorecard-"] p,
    [class*="st-key-scorecard-"] span {{
        color: {CARD_TEXT_PRIMARY} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Scorecard")
st.caption(
    f"The most common notes and accords across everything you've saved "
    f"(liked and recommended perfumes combined), top {TOP_N} each."
)

history = load_saved_history()


def render_tier_card(tier_label, tier_key):
    """Show the top 3 distinct count-levels for one tier, in a small card,
    one numbered line per rank (tied notes share a rank number and are
    joined on the same line with commas, e.g. "1. bergamot, pear (3)").
    1st place is shown in a stronger colour (CARD_TEXT_PRIMARY), 2nd and
    3rd place in a muted colour (CARD_TEXT_SECONDARY), so the strongest
    pattern stands out visually from the runners-up. Shows nothing
    noteworthy if the highest count is only 1 (no repeats across saved
    perfumes yet), per most_common_per_tier's rule.
    """
    with st.container(border=True, key=f"scorecard-tier-{tier_key}"):
        st.markdown(f"**{tier_label}**")
        ranks = most_common_per_tier(history["perfumes"], tier_key, max_ranks=TIER_MAX_RANKS)
        if not ranks:
            st.caption("Nothing stands out yet.")
        else:
            for rank_number, (count, notes) in enumerate(ranks, start=1):
                colour = CARD_TEXT_PRIMARY if rank_number == 1 else CARD_TEXT_SECONDARY
                joined_notes = ", ".join(notes)
                st.markdown(
                    f'<div style="color:{colour};">{rank_number}. {joined_notes} ({count})</div>',
                    unsafe_allow_html=True,
                )


tier_col_top, tier_col_heart, tier_col_base = st.columns(3)

with tier_col_top:
    render_tier_card("Top notes", "top_notes")

with tier_col_heart:
    render_tier_card("Heart notes", "mid_notes")

with tier_col_base:
    render_tier_card("Base notes", "base_notes")


def render_ranked_table(counts, label):
    """Render a name/count dict as a simple ranked markdown table, sorted
    by count descending, capped at TOP_N. Ties are broken alphabetically
    for a stable, predictable order.
    """
    if not counts:
        st.caption(f"No {label} saved yet.")
        return

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]

    with st.container(border=True, key=f"scorecard-{label}"):
        header_cols = st.columns([1, 4, 1])
        header_cols[0].markdown("**Rank**")
        header_cols[1].markdown(f"**{label.capitalize()}**")
        header_cols[2].markdown("**Count**")

        for rank, (name, count) in enumerate(ranked, start=1):
            row_cols = st.columns([1, 4, 1])
            row_cols[0].markdown(str(rank))
            row_cols[1].markdown(name)
            row_cols[2].markdown(str(count))


col_notes, col_accords = st.columns(2)

with col_notes:
    st.markdown("## Notes")
    render_ranked_table(history["notes"], "notes")

with col_accords:
    st.markdown("## Accords")
    render_ranked_table(history["accords"], "accords")
