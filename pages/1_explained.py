"""
"Explained" page: how the recommender works.

Written for someone with no maths or technical background: explains what
the recommender is actually doing, step by step, using plain language,
concrete examples, and diagrams rather than formulas or code. Anything
more technical (IDF weighting details, cosine similarity, the actual
config6 formula) is described through analogy first, with the plain-
language version always coming before any hint of the underlying maths.
"""

import pickle

import numpy as np
import streamlit as st

from constants import (
    ACCENT_PRIMARY,
    BACKGROUND_DARK,
    BACKGROUND_LIGHT,
    CARD_BACKGROUND,
    CARD_TEXT_PRIMARY,
    CARD_TEXT_SECONDARY,
    CONFIG6_OBJECTS_PATH,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from explainer_diagrams import alpha_blend_chart, notes_overlap_html, rarity_weighting_bar
from recommender import get_index_factory, recommend_combined

st.set_page_config(page_title="Explained", layout="wide")


@st.cache_resource
def load_objects():
    """Load the fitted config6 objects, same as home.py, so this page can
    compute real examples from the person's own current picks rather than
    only ever showing made-up placeholder numbers.
    """
    with open(CONFIG6_OBJECTS_PATH, "rb") as f:
        return pickle.load(f)


def get_current_picks():
    """Read the person's currently picked liked perfumes/notes from
    st.session_state, the same keys home.py itself uses. Streamlit shares
    session_state across all pages in one browser session, so this only
    finds anything if the person has visited home.py in this session and
    picked something there. Returns empty lists rather than raising if the
    keys don't exist yet (e.g. this page was opened first, before home.py).
    """
    liked_labels = st.session_state.get("liked_perfume_labels", [])
    liked_notes = st.session_state.get("liked_note_names", [])
    return liked_labels, liked_notes


def compute_note_idf_weights(note_matrix):
    """Same smoothed IDF formula as prep_data.py's compute_idf_weights_sparse
    (log((n+1)/(df+1)) + 1), recomputed here since only the already-blended
    config6_matrix is saved to disk, not the standalone note IDF weights.
    """
    n_fragrances = note_matrix.shape[0]
    doc_freq = np.asarray(note_matrix.sum(axis=0)).flatten()
    return np.log((n_fragrances + 1) / (doc_freq + 1)) + 1


def pick_common_and_rare_note(liked_labels, liked_notes, df, label_to_id, note_matrix, mlb_notes):
    """Gather every candidate note from current picks (both directly
    picked notes and all notes from picked perfumes), look up each one's
    real IDF weight, and return the (common_note, common_weight,
    rare_note, rare_weight) pair with the largest weight gap. Ties or a
    single-candidate case are handled by just taking whatever spread
    exists, per the person's own instruction to show the best available
    contrast even if it isn't dramatic. Returns None if fewer than 2
    distinct candidate notes are available at all.
    """
    candidate_notes = set(liked_notes)
    for label in liked_labels:
        row = df[df["id"] == label_to_id[label]].iloc[0]
        candidate_notes.update(row["all_notes"])

    note_idf = compute_note_idf_weights(note_matrix)
    classes = list(mlb_notes.classes_)
    class_index = {name: i for i, name in enumerate(classes)}

    weighted = [
        (name, note_idf[class_index[name]])
        for name in candidate_notes
        if name in class_index
    ]

    if len(weighted) < 2:
        return None

    weighted.sort(key=lambda pair: pair[1])
    lowest_name, lowest_weight = weighted[0]
    highest_name, highest_weight = weighted[-1]
    return lowest_name, lowest_weight, highest_name, highest_weight


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
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Explained")
st.caption("make sense out of your recommendations")

st.markdown("## The big idea")
st.markdown(
    """
a fragrance is made up of notes. and similar notes are then grouped up into accords. we can compare fragrances by their overlap.
"""
)

st.markdown("## Step 1: compare notes")
st.markdown(
    """
more shared notes means a higher note similarity score
"""
)

objects = load_objects()
df = objects["df"]
liked_labels, liked_notes = get_current_picks()
label_to_id = dict(objects["display_options"])

if len(liked_labels) >= 2:
    perfume_a_label, perfume_b_label = liked_labels[0], liked_labels[1]
    row_a = df[df["id"] == label_to_id[perfume_a_label]].iloc[0]
    row_b = df[df["id"] == label_to_id[perfume_b_label]].iloc[0]

    st.markdown(
        notes_overlap_html(
            fragrance_a_name=perfume_a_label,
            fragrance_a_notes=row_a["all_notes"],
            fragrance_b_name=perfume_b_label,
            fragrance_b_notes=row_b["all_notes"],
            card_bg=CARD_BACKGROUND,
            card_text=CARD_TEXT_PRIMARY,
            accent=ACCENT_PRIMARY,
        ),
        unsafe_allow_html=True,
    )
else:
    st.info(
        "Pick at least 2 liked perfumes on the home page to see a real comparison here."
    )

st.markdown("## Step 2: weight by rarity")
st.markdown(
    """
rare notes are a stronger sign of similarity than common ones. so we put more weight on them
"""
)

note_matrix = objects["note_matrix"]
mlb_notes = objects["mlb_notes"]
tier_pick = pick_common_and_rare_note(liked_labels, liked_notes, df, label_to_id, note_matrix, mlb_notes)

if tier_pick is not None:
    common_note, common_weight, rare_note, rare_weight = tier_pick
    st.plotly_chart(
        rarity_weighting_bar(
            common_note=common_note,
            common_note_weight=float(common_weight),
            rare_note=rare_note,
            rare_note_weight=float(rare_weight),
            bar_colour=ACCENT_PRIMARY,
            text_colour=TEXT_PRIMARY,
        ),
        use_container_width=True,
    )
else:
    st.info(
        "Pick at least 2 distinct notes (directly, or via liked perfumes) on the "
        "home page to see a real rarity comparison here."
    )

st.markdown("## Step 3: compare accords")
st.markdown(
    """
accords are compared the same way notes are. so we get a accords similarity score too
"""
)

st.markdown("## Step 4: blend perfumes & notes similarity scores ")
st.markdown(
    """
the **balance slider** controls how much weight either the perfumes or the notes get
"""
)

ALPHA_STEPS = [0.0, 0.25, 0.5, 0.75, 1.0]

top_names_by_alpha = None
if liked_labels and liked_notes:
    liked_fids = [label_to_id[label] for label in liked_labels]
    note_matrix = objects["note_matrix"]
    mlb_notes = objects["mlb_notes"]
    config6_matrix = objects["config6_matrix"]
    get_index = get_index_factory(df)

    combined_scores = []
    top_names_by_alpha = []
    for a in ALPHA_STEPS:
        result, _ = recommend_combined(
            liked_fids=liked_fids,
            liked_note_names=liked_notes,
            alpha=a,
            top_k=1,
            df=df,
            note_matrix=note_matrix,
            mlb_notes=mlb_notes,
            config6_matrix=config6_matrix,
            get_index=get_index,
        )
        if result is not None and len(result):
            top_row = result.iloc[0]
            combined_scores.append(float(top_row["similarity"]))
            top_names_by_alpha.append(top_row["name"])
        else:
            combined_scores.append(0.0)
            top_names_by_alpha.append("(no result)")

st.plotly_chart(
    alpha_blend_chart(
        alphas=ALPHA_STEPS,
        combined_scores=combined_scores if top_names_by_alpha else [0.31, 0.44, 0.5, 0.56, 0.69],
        top_names=top_names_by_alpha if top_names_by_alpha else ["Fragrance X"] * 5,
        alpha=0.5,
        bar_colour=CARD_TEXT_SECONDARY,
        accent_colour=ACCENT_PRIMARY,
        text_colour=TEXT_PRIMARY,
    ),
    use_container_width=True,
)

if top_names_by_alpha is None:
    st.info(
        "Pick at least one liked perfume AND at least one liked note on the home page "
        "to see a real blended score here."
    )

st.markdown("## Step 5: putting it together")
st.markdown(
    """
recommended fragrances are sorted from highest combined score to lowest
"""
)
