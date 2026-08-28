"""
Shared config6 recommendation logic, extracted from home.py so it can be
imported by other pages (e.g. pages/1_explained.py, which needs to run a
real recommendation to show a genuine notes/perfumes similarity example)
without re-executing home.py's own Streamlit UI code, which would happen
if home.py itself were imported as a module.

DUPE_THRESHOLD is imported from constants rather than redefined here, so
there's a single source of truth for the dupe-exclusion cutoff.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from constants import DUPE_THRESHOLD


def get_index_factory(df):
    """Build a get_index closure matching the notebook's own get_index function."""
    def get_index(fid):
        matches = df.index[df["id"] == fid]
        return matches[0] if len(matches) else None
    return get_index


def resolve_liked_fids(liked_fids, get_index):
    valid_idxs = []
    dropped = []
    for fid in liked_fids:
        idx = get_index(fid)
        if idx is None:
            dropped.append(fid)
        else:
            valid_idxs.append(idx)
    return valid_idxs, dropped


def notes_scores_all(liked_note_names, note_matrix, mlb_notes):
    """Binary cosine similarity between picked notes and every fragrance.

    Picked notes are binary, not IDF-weighted: a manual pick expresses
    preference, not rarity, so weighting by how common the note is would
    misrepresent the user's intent.
    """
    query_vector = mlb_notes.transform([liked_note_names])
    return cosine_similarity(query_vector, note_matrix).flatten()


def recommend_combined(liked_fids, liked_note_names, alpha, top_k, df, note_matrix,
                        mlb_notes, config6_matrix, get_index, exclude_dupes=True,
                        dupe_threshold=DUPE_THRESHOLD):
    """Frozen config6 recommendation logic, adapted for the app's already-
    validated inputs (the UI only ever passes ids and note names known to
    exist, so the notebook's warn-and-drop validation isn't needed here).
    """
    liked_idxs, dropped_fids = resolve_liked_fids(liked_fids, get_index) if liked_fids else ([], [])

    notes_scores = notes_scores_all(liked_note_names, note_matrix, mlb_notes) if liked_note_names else None
    perfumes_scores = None
    if liked_idxs:
        query_vector = np.asarray(config6_matrix[liked_idxs].mean(axis=0))
        perfumes_scores = cosine_similarity(query_vector, config6_matrix).flatten()

    if notes_scores is None and perfumes_scores is None:
        return None, dropped_fids
    elif notes_scores is None:
        scores = perfumes_scores
    elif perfumes_scores is None:
        scores = notes_scores
    else:
        scores = alpha * notes_scores + (1 - alpha) * perfumes_scores

    ranked_idxs = np.argsort(scores)[::-1]

    exclude_set = set(liked_idxs)
    result_idxs, result_scores = [], []
    for idx in ranked_idxs:
        if idx in exclude_set:
            continue
        if exclude_dupes and liked_idxs:
            too_close = any(
                cosine_similarity(config6_matrix[idx], config6_matrix[li])[0][0] > dupe_threshold
                for li in liked_idxs
            )
            if too_close:
                continue
        result_idxs.append(idx)
        result_scores.append(scores[idx])
        if len(result_idxs) == top_k:
            break

    result = df.iloc[result_idxs][
        ["name", "brand", "year", "all_notes", "top_notes", "mid_notes", "base_notes", "accords"]
    ].copy()
    result["similarity"] = result_scores
    if notes_scores is not None:
        result["notes_similarity"] = [notes_scores[i] for i in result_idxs]
    if perfumes_scores is not None:
        result["perfumes_similarity"] = [perfumes_scores[i] for i in result_idxs]

    return result.reset_index(drop=True), dropped_fids
