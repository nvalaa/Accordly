"""
Prep script for the config6 Streamlit app.

Reads data/perfumes_final.pkl, rebuilds the fitted config6 objects exactly
as in final_capstone_notebook.ipynb, and pickles them to
data/config6_objects.pkl for the app to load directly. Run this once after
any change to perfumes_final.pkl, not on every app startup.

perfumes_final.pkl already has the near-duplicate note merges (NOTE_MERGES
below) applied and saved in, and already stores all_notes as a native
Python list and accords as a native Python dict, so no parsing or merging
is needed here.

Usage:
    python prep_data.py
"""

import pickle

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.preprocessing import MultiLabelBinarizer

from constants import BLEND_RATIO, CONFIG6_OBJECTS_PATH, DATA_DIR

PKL_PATH = f"{DATA_DIR}/perfumes_final.pkl"
OUTPUT_PATH = CONFIG6_OBJECTS_PATH

# Near-duplicate note name merges, checked individually rather than blind
# fuzzy-matched. Each pair was confirmed as a genuine spelling variant,
# typo, or formatting difference of the same underlying note, not a real
# olfactory distinction. The less frequent spelling in each pair is folded
# into the more frequent one.
#
# NOTE: this has already been applied and saved into perfumes_final.pkl.
# It is kept here purely as a documented record of what was merged and why
# (see apply_note_merges below, which is not called from main()); do not
# re-run it against perfumes_final.pkl, since the merges are already baked
# in, and NOTE_MERGES/apply_note_merges only exist here for provenance.
#
# Three close-spelling candidates were checked and confirmed as NOT
# duplicates, and are deliberately excluded from this list:
#   - barberry / bearberry: different plants
#   - mahonia / mahonial: mahonial is a real, distinct synthetic aroma
#     molecule, unrelated to the mahonia plant genus
#   - ambrein / ambreine: distinct compounds with different CAS numbers
#     (ambrein is a triterpene alcohol from ambergris; ambreine is a
#     separate refined accord/material)
NOTE_MERGES = {
    "ambrox® super": "ambrox super",
    "angels trumpet": "angel's trumpet",
    "blackcurrant": "black currant",
    "californian orange": "california orange",
    "camelia": "camellia",
    "canadian balsam": "canada balsam",
    "cashmirwood": "cashmir wood",
    "cereals": "cereal",
    "coton candy": "cotton candy",
    "ethyl vanilin": "ethylvanillin",
    "gaiac wood": "guaiac wood",
    "gurjun balsam": "gurjan balsam",
    "lime (linden) blossom": "lime (linden blossom)",
    "marshamallow": "marshmallow",
    "mirabella plum": "mirabelle plum",
    "narciussus": "narcissus",
    "oak moss": "oakmoss",
    "passion fruit": "passionfruit",
    "pitosporum": "pittosporum",
    "quandong desert peach": "quandong, desert peach",
    "raspberry bloom": "raspberry blossom",
    "sandalowood": "sandalwood",
    "sea shells": "seashells",
    "sicilian citruses": "sicilian citrus",
    "vanila": "vanilla",
    "virginian cedar": "virginia cedar",
    "water notes": "watery notes",
    "white tabacco": "white tobacco",
    "white wood": "white woods",
    "woodsy notes": "woody notes",
    "st john's wort": "st. john's wort",
    "tropical fruit": "tropical fruits",
}


def apply_note_merges(notes_list):
    """Rename near-duplicate note spellings to their canonical form, per
    NOTE_MERGES, and de-duplicate the result (a fragrance listing both the
    typo and the correct spelling should count that note once).
    """
    return sorted(set(NOTE_MERGES.get(n, n) for n in notes_list))


def compute_idf_weights_sparse(binary_matrix):
    """Same smoothed IDF formula as the primary project: log((n+1)/(df+1)) + 1."""
    n_fragrances = binary_matrix.shape[0]
    doc_freq = np.asarray(binary_matrix.sum(axis=0)).flatten()
    return np.log((n_fragrances + 1) / (doc_freq + 1)) + 1


def normalise_rows_sparse(matrix):
    """L2-normalise each row of a sparse matrix to unit length."""
    norms = sparse.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1
    return matrix.multiply(1 / norms[:, None]).tocsr()


def build_display_options(df):
    """Build the (label, id) options a dropdown/autocomplete shows so a user can
    pick a liked perfume unambiguously, without needing to know its id.

    Disambiguation is layered, each step only applied where the previous one
    wasn't already enough:
      1. "name (brand)" resolves most collisions.
      2. where name+brand still collides, year is appended, e.g.
         "Samsara Eau de Parfum (Guerlain, 1989)" vs "..., 2021".
      3. where year is missing or identical across the colliding rows, id is
         appended as a final, guaranteed-unique fallback.
    """
    name_brand = df["name"] + " (" + df["brand"] + ")"
    labels = name_brand.copy()

    still_colliding = name_brand.duplicated(keep=False)
    with_year = name_brand.str.rstrip(")") + ", " + df["year"].astype("Int64").astype(str) + ")"
    labels = labels.where(~still_colliding | df["year"].isna(), with_year)

    still_colliding_after_year = labels.duplicated(keep=False) & still_colliding
    labels = labels.where(~still_colliding_after_year, labels + " [id " + df["id"].astype(str) + "]")

    return list(zip(labels.tolist(), df["id"].tolist()))


def main():
    df = pd.read_pickle(PKL_PATH)

    mlb_notes = MultiLabelBinarizer(sparse_output=True)
    note_matrix = mlb_notes.fit_transform(df["all_notes"]).tocsr()

    all_accord_names = sorted(set(a for accs in df["accords"] for a in accs.keys()))
    accord_index = {name: i for i, name in enumerate(all_accord_names)}

    rows, cols, vals = [], [], []
    for i, accs in enumerate(df["accords"]):
        for a in accs.keys():
            rows.append(i)
            cols.append(accord_index[a])
            vals.append(1)
    accord_bin_matrix = sparse.csr_matrix(
        (vals, (rows, cols)), shape=(len(df), len(all_accord_names))
    )

    note_idf = compute_idf_weights_sparse(note_matrix)
    accord_idf = compute_idf_weights_sparse(accord_bin_matrix)

    note_idf_matrix = note_matrix.multiply(note_idf).tocsr()
    accord_idf_matrix = accord_bin_matrix.multiply(accord_idf).tocsr()

    note_idf_norm = normalise_rows_sparse(note_idf_matrix.astype(float))
    accord_idf_norm = normalise_rows_sparse(accord_idf_matrix.astype(float))

    config6_matrix = sparse.hstack([
        note_idf_norm * BLEND_RATIO,
        accord_idf_norm * (1 - BLEND_RATIO),
    ]).tocsr()

    display_options = build_display_options(df)

    objects = {
        "df": df,
        "note_matrix": note_matrix,
        "mlb_notes": mlb_notes,
        "config6_matrix": config6_matrix,
        "display_options": display_options,
        "blend_ratio": BLEND_RATIO,
    }

    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(objects, f)

    print(f"fragrances: {len(df)}")
    print(f"note_matrix: {note_matrix.shape}")
    print(f"config6_matrix: {config6_matrix.shape}")
    print(f"display options: {len(display_options)}")
    print(f"written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
