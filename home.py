"""
Streamlit app for the config6 fragrance recommender.

Loads the fitted objects produced by prep_data.py (data/config6_objects.pkl)
rather than rebuilding them from perfumes.csv on every run. Run prep_data.py
once, or after any change to perfumes.csv, before starting this app.

Usage:
    streamlit run home.py
"""

import pickle
import unicodedata
import warnings

import pandas as pd
import streamlit as st
from streamlit_searchbox import st_searchbox

from constants import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BACKGROUND_DARK,
    BACKGROUND_LIGHT,
    BORDER_MUTED,
    CARD_BACKGROUND,
    CARD_TEXT_PRIMARY,
    CARD_TEXT_SECONDARY,
    CHIP_BACKGROUND,
    CONFIG6_OBJECTS_PATH,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from recommender import get_index_factory, recommend_combined
from saved_history import add_perfume_to_history, load_saved_history, save_history_to_disk

OBJECTS_PATH = CONFIG6_OBJECTS_PATH


def normalise_search_key(text):
    """Strip accents and lowercase text so search matching ignores both.

    Streamlit's multiselect searches against the literal option value, so
    typing "Idole" would not find "Idôle" by default. Normalising both the
    option keys and (implicitly, via Streamlit's own lowercasing) the typed
    query to a common accent-free, lowercase form makes search behave the
    way a user expects, while format_func still displays the original,
    correctly-accented name.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.lower()


@st.cache_resource
def load_objects():
    """Load the fitted config6 objects once per app session, not per query.

    st.cache_resource keeps this out of Streamlit's normal rerun cycle: every
    widget interaction reruns the whole script top to bottom, and reloading a
    131,930-row sparse matrix from disk on every slider move would make the
    app unusable.
    """
    with open(OBJECTS_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_resource
def build_search_indexes(_df, _label_to_id, _all_note_names):
    """Build the (search_key, display_value) lists used by search_perfumes
    and search_notes, once per session rather than on every rerun.

    Streamlit reruns the whole script top to bottom on every widget
    interaction (every keystroke in a search box, every button click
    anywhere on the page). Without caching, this function's ~510ms cost of
    rebuilding a 129,325-item list would repeat on every single rerun, which
    dwarfs the ~75ms the actual search itself takes and is the dominant
    cause of the search boxes feeling slow. st.cache_resource skips
    recomputation as long as the underlying data object is the same one
    already in memory (leading underscores tell Streamlit not to hash these
    large arguments for change-detection, which would itself be slow;
    caching keys on the object's identity instead, which is safe here since
    df/label_to_id are only ever built once at startup).
    """
    all_labels = sorted(_label_to_id.keys())

    if "search_key" in _df.columns and "search_key_brand" in _df.columns:
        id_to_search_key = dict(zip(_df["id"], _df["search_key"] + " " + _df["search_key_brand"]))
        perfume_pairs = [
            (id_to_search_key.get(_label_to_id[label], normalise_search_key(label)), label)
            for label in all_labels
        ]
    else:
        perfume_pairs = [(normalise_search_key(label), label) for label in all_labels]

    note_pairs = [(normalise_search_key(name), name) for name in _all_note_names]

    return perfume_pairs, note_pairs


def format_accords(accords_dict):
    """Render an accord dict as a comma-separated string, strongest first."""
    if not accords_dict:
        return "none recorded"
    sorted_accords = sorted(accords_dict.items(), key=lambda x: x[1], reverse=True)
    return ", ".join(name for name, _ in sorted_accords)


def format_notes(notes_list):
    """Render a notes list as a comma-separated string."""
    if not notes_list:
        return "none recorded"
    return ", ".join(notes_list)


def render_note_breakdown(top_notes, mid_notes, base_notes, all_notes):
    """Render the note breakdown for a perfume card. Prefers showing the
    top/heart/base tier split, but some perfumes in the dataset never had
    their notes categorised into pyramid tiers (all three tier lists are
    empty even though all_notes has real data) -- for those, three empty
    "none recorded" lines would be actively unhelpful, since the person
    can see the recommendation clearly used real note data (a genuine
    notes similarity score) despite no tier breakdown existing to show.
    So when every tier is empty but all_notes isn't, this falls back to a
    single flat "Notes: ..." line instead of the tier breakdown.
    """
    has_tier_data = bool(top_notes) or bool(mid_notes) or bool(base_notes)
    if has_tier_data:
        st.caption(f"Top notes: {format_notes(top_notes)}")
        st.caption(f"Heart notes: {format_notes(mid_notes)}")
        st.caption(f"Base notes: {format_notes(base_notes)}")
    else:
        st.caption(f"Notes: {format_notes(all_notes)}")


st.set_page_config(page_title="Accordly", layout="wide")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_LIGHT};
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stAppViewContainer"] h1 {{
        color: #8A9A28;
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
    .stButton > button {{
        background-color: {ACCENT_PRIMARY};
        color: {CARD_TEXT_PRIMARY};
        border: none;
    }}
    .stButton > button:hover {{
        background-color: {ACCENT_HOVER};
        color: {CARD_TEXT_PRIMARY};
    }}
    [class*="st-key-remove_perfume_"] [data-testid="stBaseButton-secondary"],
    [class*="st-key-remove_note_"] [data-testid="stBaseButton-secondary"] {{
        width: 1.1rem !important;
        height: 1.1rem !important;
        max-width: 1.1rem !important;
        min-width: 1.1rem !important;
        max-height: 1.1rem !important;
        min-height: 1.1rem !important;
        aspect-ratio: 1 / 1 !important;
        padding: 0 !important;
        line-height: 1;
        font-size: 0.6rem;
        border-radius: 50% !important;
        box-sizing: border-box;
        align-self: center;
    }}
    [data-testid="stCaptionContainer"] {{
        color: {TEXT_SECONDARY};
    }}
    [data-testid="stAlert"],
    [data-testid="stAlert"] > div {{
        background-color: {CHIP_BACKGROUND};
        background-image: none;
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span,
    [data-testid="stAlert"] div {{
        color: {TEXT_PRIMARY};
    }}
    [class*="st-key-rec-card-"] {{
        background-color: {CARD_BACKGROUND} !important;
        border: 1px solid {BORDER_MUTED} !important;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }}
    [class*="st-key-rec-card-"] [data-testid="stCaptionContainer"] {{
        color: {CARD_TEXT_SECONDARY} !important;
    }}
    [class*="st-key-rec-card-"] p,
    [class*="st-key-rec-card-"] span {{
        color: {CARD_TEXT_PRIMARY} !important;
    }}
    [class*="st-key-rec-card-"] [data-testid="stMetricValue"],
    [class*="st-key-rec-card-"] [data-testid="stMetricLabel"] {{
        color: {CARD_TEXT_PRIMARY} !important;
    }}
    .liked-chip {{
        background-color: {CHIP_BACKGROUND};
        color: {TEXT_PRIMARY};
        border-radius: 6px;
        padding: 6px 10px;
        margin-bottom: 6px;
        font-size: 14px;
    }}
    [data-testid="stAlert"] {{
        background-color: {CHIP_BACKGROUND} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    [data-testid="stAlert"] p {{
        color: {TEXT_PRIMARY} !important;
    }}
    /* Slider: recolour track, thumb and value label to match the theme */
    [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {{
        background-color: {ACCENT_PRIMARY} !important;
    }}
    [data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {{
        background: {ACCENT_PRIMARY} !important;
    }}
    [data-testid="stSlider"] [data-testid="stThumbValue"] {{
        color: {ACCENT_PRIMARY} !important;
    }}
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] {{
        color: {TEXT_SECONDARY} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Accordly")
st.caption("vala's rarity-weighted perfume recommender :D")

objects = load_objects()
df = objects["df"]
note_matrix = objects["note_matrix"]
mlb_notes = objects["mlb_notes"]
config6_matrix = objects["config6_matrix"]
display_options = objects["display_options"]
get_index = get_index_factory(df)

label_to_id = dict(display_options)
all_note_names = sorted(mlb_notes.classes_)

perfume_search_pairs, note_search_pairs = build_search_indexes(
    df, label_to_id, all_note_names
)


def matches_all_words(query_key, search_key):
    """Check every word in the typed query appears somewhere in the search
    key, regardless of what order they were typed in. A plain substring
    check (query_key in search_key) only succeeds if the words happen to be
    typed in the same order they're stored ("name brand"), so someone
    typing "brand name" instead would find nothing even though every word
    they typed is genuinely present. Splitting on whitespace and requiring
    each word to appear somewhere fixes that, without needing true fuzzy
    (edit-distance) matching.
    """
    query_words = query_key.split()
    return all(word in search_key for word in query_words)


def search_perfumes(searchterm):
    """search_function for st_searchbox: returns matching display labels for
    whatever's typed, accent- and case-insensitive, word-order-independent,
    sorted alphabetically. Streamlit-searchbox calls this on every keystroke
    and displays exactly what it returns, so the dropdown only ever shows
    clean, correctly-accented names, never the normalised search key itself.
    """
    if not searchterm.strip():
        return []
    query_key = normalise_search_key(searchterm)
    matches = sorted(label for key, label in perfume_search_pairs if matches_all_words(query_key, key))
    return matches[:25]


def search_notes(searchterm):
    """search_function for st_searchbox, notes version."""
    if not searchterm.strip():
        return []
    query_key = normalise_search_key(searchterm)
    matches = sorted(name for key, name in note_search_pairs if matches_all_words(query_key, key))
    return matches[:25]


if "liked_perfume_labels" not in st.session_state:
    st.session_state.liked_perfume_labels = []
if "liked_note_names" not in st.session_state:
    st.session_state.liked_note_names = []

input_col, results_col = st.columns([1, 2])

with input_col:
    st.subheader("Your Likes")

    st.caption("Perfumes you like")
    picked_perfume = st_searchbox(
        search_perfumes,
        key="perfume_searchbox",
        placeholder="Search a perfume, e.g. libre",
        clear_on_submit=False,
        edit_after_submit="current",
    )
    if picked_perfume and picked_perfume not in st.session_state.liked_perfume_labels:
        st.session_state.liked_perfume_labels.append(picked_perfume)

    for label in list(st.session_state.liked_perfume_labels):
        chip_cols = st.columns([8, 1])
        chip_cols[0].markdown(f'<div class="liked-chip">{label}</div>', unsafe_allow_html=True)
        if chip_cols[1].button("✕", key=f"remove_perfume_{label}"):
            st.session_state.liked_perfume_labels.remove(label)
            st.rerun()

    st.caption("Notes you like")
    picked_note = st_searchbox(
        search_notes,
        key="note_searchbox",
        placeholder="Search a note, e.g. violet",
        clear_on_submit=False,
        edit_after_submit="current",
    )
    if picked_note and picked_note not in st.session_state.liked_note_names:
        st.session_state.liked_note_names.append(picked_note)

    for name in list(st.session_state.liked_note_names):
        chip_cols = st.columns([8, 1])
        chip_cols[0].markdown(f'<div class="liked-chip">{name}</div>', unsafe_allow_html=True)
        if chip_cols[1].button("✕", key=f"remove_note_{name}"):
            st.session_state.liked_note_names.remove(name)
            st.rerun()

    selected_labels = st.session_state.liked_perfume_labels
    selected_notes = st.session_state.liked_note_names

    alpha = st.slider(
        "Balance: notes vs perfumes",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="0 relies entirely on liked perfumes & 1 relies entirely on liked notes",
    )

    top_k = st.slider("Number of recommendations", min_value=5, max_value=50, value=10, step=5)

    run_query = st.button("Get recommendations", type="primary")

    if st.button("Save current selection"):
        if not selected_labels:
            st.warning("Pick at least one liked perfume before saving.")
        else:
            history = load_saved_history()
            for label in selected_labels:
                fid = label_to_id[label]
                row = df[df["id"] == fid].iloc[0]
                add_perfume_to_history(
                    history,
                    name=row["name"],
                    brand=row["brand"],
                    year=row["year"] if pd.notna(row["year"]) else None,
                    tag="liked",
                    all_notes=row["all_notes"],
                    accords=row["accords"],
                    top_notes=row["top_notes"],
                    mid_notes=row["mid_notes"],
                    base_notes=row["base_notes"],
                )
            save_history_to_disk(history)
            st.success(f"Saved {len(selected_labels)} perfume(s) to your saved history.")

with results_col:
    if run_query:
        liked_fids = [label_to_id[label] for label in selected_labels]

        if not liked_fids and not selected_notes:
            st.warning("Pick at least one liked perfume or one liked note before running a query.")
        else:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result, dropped_fids = recommend_combined(
                    liked_fids=liked_fids,
                    liked_note_names=selected_notes,
                    alpha=alpha,
                    top_k=top_k,
                    df=df,
                    note_matrix=note_matrix,
                    mlb_notes=mlb_notes,
                    config6_matrix=config6_matrix,
                    get_index=get_index,
                    exclude_dupes=True,
                )

            if result is None:
                st.error("No valid input to score against. Check your selections and try again.")
            else:
                has_notes_side = "notes_similarity" in result.columns
                has_perfumes_side = "perfumes_similarity" in result.columns

                if has_notes_side and has_perfumes_side:
                    st.info(f"Blending both inputs at alpha={alpha:.2f} (notes weight) / {1 - alpha:.2f} (perfumes weight).")
                elif has_notes_side:
                    st.info("Scored on liked notes only. Alpha has no effect: no liked perfumes were given.")
                elif has_perfumes_side:
                    st.info("Scored on liked perfumes only. Alpha has no effect: no liked notes were given.")

                st.subheader(f"Top {len(result)} recommendations")

                for rank, (_, row) in enumerate(result.iterrows()):
                    with st.container(border=True, key=f"rec-card-{rank}"):
                        header_cols = st.columns([3, 1])
                        with header_cols[0]:
                            year_str = f", {int(row['year'])}" if pd.notna(row["year"]) else ""
                            st.markdown(f"**{row['name']}** ({row['brand']}{year_str})")
                        with header_cols[1]:
                            st.metric("Combined score", f"{row['similarity']:.3f}")

                        breakdown_cols = st.columns(2)
                        with breakdown_cols[0]:
                            if has_notes_side:
                                st.caption(f"Notes similarity: {row['notes_similarity']:.3f}")
                            if has_perfumes_side:
                                st.caption(f"Perfumes similarity: {row['perfumes_similarity']:.3f}")

                        render_note_breakdown(row["top_notes"], row["mid_notes"], row["base_notes"], row["all_notes"])
                        st.caption(f"Accords: {format_accords(row['accords'])}")

                        if st.button("Save this recommendation", key=f"save-rec-{rank}"):
                            history = load_saved_history()
                            add_perfume_to_history(
                                history,
                                name=row["name"],
                                brand=row["brand"],
                                year=row["year"] if pd.notna(row["year"]) else None,
                                tag="recommended",
                                all_notes=row["all_notes"],
                                accords=row["accords"],
                                top_notes=row["top_notes"],
                                mid_notes=row["mid_notes"],
                                base_notes=row["base_notes"],
                            )
                            save_history_to_disk(history)
                            st.success(f"Saved {row['name']} to your saved history.")

    else:
        st.markdown(
            "<div style='text-align: left;'>pick perfumes and/or notes to get your recommendations</div>",
            unsafe_allow_html=True,
        )
