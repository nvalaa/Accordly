"""
Persistent saved-history storage, shared between home.py (where perfumes
get saved) and pages/2_saved.py (where the saved history is viewed and
edited).

Stored as a single JSON file (data/saved_history.json) with three parts:

    {
        "perfumes": [
            {"name": ..., "brand": ..., "year": ..., "tag": "liked" | "recommended",
             "all_notes": [...], "top_notes": [...], "mid_notes": [...],
             "base_notes": [...], "accords": {...}},
            ...
        ],
        "notes": {"vanilla": 2, "musk": 1, ...},
        "accords": {"sweet": 3, ...}
    }

"perfumes" is a list, since the same name/brand could plausibly appear
more than once with a different tag would be unusual but isn't blocked --
in practice a person wouldn't save the same perfume as both liked and
recommended, so no de-duplication is enforced here. "notes" and "accords"
are dicts mapping name -> count, incremented every time a perfume
contributing that note/accord is saved, and used later for a "most common"
scorecard. Removing a note/accord always deletes the entry outright,
regardless of its count. "notes" is built from all_notes (the flattened,
tier-agnostic list) regardless of tier, so it's unaffected by the
per-tier fields below.

top_notes/mid_notes/base_notes are stored per perfume (not counted/
aggregated the way notes/accords are) so that individual perfume cards
can show a tier breakdown, and the scorecard page can compute its own
per-tier "most common" summary directly from the perfumes list.

All three lists are otherwise independent once populated: removing a
perfume does not touch the notes/accords counts it originally
contributed, and removing a note/accord does not touch any perfume.
"""

import json
import os

from constants import DATA_DIR

SAVED_HISTORY_PATH = f"{DATA_DIR}/saved_history.json"

EMPTY_HISTORY = {"perfumes": [], "notes": {}, "accords": {}}


def load_saved_history():
    """Read the saved history from disk, returning an empty structure if
    the file doesn't exist yet (e.g. first run) rather than raising.
    """
    if not os.path.exists(SAVED_HISTORY_PATH):
        return {"perfumes": [], "notes": {}, "accords": {}}
    with open(SAVED_HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {"perfumes": [], "notes": {}, "accords": {}}
    # Defensive defaults in case an older/partial file is missing a key.
    data.setdefault("perfumes", [])
    data.setdefault("notes", {})
    data.setdefault("accords", {})
    return data


def save_history_to_disk(history):
    """Write the full history dict back to disk, overwriting the file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SAVED_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_perfume_to_history(history, name, brand, year, tag, all_notes, accords,
                            top_notes=None, mid_notes=None, base_notes=None):
    """Add one perfume to the saved history with the given tag ("liked" or
    "recommended"), and increment the count for each of its notes and
    accords. Mutates history in place and also returns it, for convenience.

    top_notes/mid_notes/base_notes are optional (default to empty lists)
    so this still works against a data source that doesn't provide tier
    information; when omitted, cards showing tier breakdown simply have
    nothing to display for this perfume.

    year/accord values are cast to plain Python types (float/int) rather
    than left as whatever numpy scalar type pandas produced, since numpy
    types aren't reliably JSON-serialisable across all versions of the
    json module, and this call is always followed by a save to disk.
    """
    history["perfumes"].append({
        "name": name,
        "brand": brand,
        "year": float(year) if year is not None else None,
        "tag": tag,
        "all_notes": list(all_notes),
        "top_notes": list(top_notes) if top_notes is not None else [],
        "mid_notes": list(mid_notes) if mid_notes is not None else [],
        "base_notes": list(base_notes) if base_notes is not None else [],
        "accords": {k: (int(v) if float(v).is_integer() else float(v)) for k, v in accords.items()},
    })

    for note in all_notes:
        history["notes"][note] = history["notes"].get(note, 0) + 1

    for accord in accords:
        history["accords"][accord] = history["accords"].get(accord, 0) + 1

    return history


def remove_perfume_from_history(history, index):
    """Remove the perfume at the given list index. Does not touch the
    notes/accords counts that perfume originally contributed, per the
    "independent once populated" rule documented at the top of this file.
    """
    if 0 <= index < len(history["perfumes"]):
        history["perfumes"].pop(index)
    return history


def remove_note_from_history(history, note_name):
    """Remove a note entry completely, regardless of its current count."""
    history["notes"].pop(note_name, None)
    return history


def remove_accord_from_history(history, accord_name):
    """Remove an accord entry completely, regardless of its current count."""
    history["accords"].pop(accord_name, None)
    return history


def most_common_per_tier(perfumes, tier_key, max_ranks=3):
    """Find the most common note(s) for a given tier ("top_notes",
    "mid_notes", or "base_notes") across all saved perfumes.

    Returns an empty list if the highest count is only 1 (no repeats yet,
    so there's no real pattern to report), otherwise returns the top
    max_ranks distinct count levels, each with every note tied at that
    count. E.g. if bergamot and pear are both at count 3, and jasmine and
    rose are both at count 2, this returns
    [(3, ["bergamot", "pear"]), (2, ["jasmine", "rose"])] -- ties at a
    given rank are never split across ranks, and a rank can have any
    number of tied notes. Notes at count 1 are never included, since a
    single occurrence isn't a repeat/pattern. Notes within a rank are
    sorted alphabetically for a stable order; ranks are sorted by count
    descending.
    """
    counts = {}
    for perfume in perfumes:
        for note in perfume.get(tier_key, []):
            counts[note] = counts.get(note, 0) + 1

    if not counts:
        return []

    highest = max(counts.values())
    if highest <= 1:
        return []

    by_count = {}
    for name, count in counts.items():
        if count <= 1:
            continue
        by_count.setdefault(count, []).append(name)

    distinct_counts = sorted(by_count.keys(), reverse=True)[:max_ranks]
    return [(count, sorted(by_count[count])) for count in distinct_counts]
