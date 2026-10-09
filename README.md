# Accordly

An explainable fragrance recommender. Pick fragrances you like, notes you like, or both, and Accordly suggests similar fragrances and shows exactly why each one was suggested.

**Live app:** https://accordly.streamlit.app/

Built as the capstone project for the Digital Futures academy.

## The problem

Rating-based recommenders favour what is popular, not what is similar in composition. The tools that do compare composition still behave as black boxes: they return a ranked list with no way to check the reasoning. Someone with real knowledge of notes and accords cannot test the machine's thinking against their own.

Accordly keeps the composition-based approach and makes every result checkable.

## What it does

- **Combined query:** search from fragrances you already like, notes you pick by hand, or both at once. Each input is scored separately, then blended per recommendation.
- **Transparent results:** every recommendation shows its combined score alongside the notes similarity and the perfumes similarity that produced it. The blend can be reconstructed exactly from its two parts.
- **Rarity weighting:** rare, distinctive notes carry more weight than common ones such as musk, because a shared rare note is a stronger signal of true similarity.
- **Adjustable blend:** a slider sets how much weight the notes side and the perfumes side each carry (alpha).
- **Near-duplicate filtering:** results too close to a liked fragrance (similarity above 0.80) are excluded by default, so the list is not just clones.

## How it works

```
raw scrape (131,930 fragrances)
  -> cleaning (note and accord parsing, empty-row removal, year merge)
  -> note spelling merges (32 variants folded together)
  -> vectorisation (IDF-weighted notes + IDF-weighted accords)
  -> combined query (liked fragrances + liked notes, alpha-weighted)
  -> ranking
  -> Streamlit app
```

- **Dataset:** 129,325 fragrances after cleaning, with 2,488 unique notes and 92 accords.
- **Fragrance vectors (`config6`):** each fragrance is represented by two fingerprints, one from its notes and one from its accords, both IDF-weighted and blended evenly (`blend_ratio = 0.5`).
- **IDF weight per note:** `log((n + 1) / (df + 1)) + 1`, so common notes are down-weighted and rare notes up-weighted.
- **Query blend:** `combined_score = alpha * notes_score + (1 - alpha) * perfumes_score`, with `alpha = 0.5` by default. Notes picked by hand are treated as binary preferences, not rarity-weighted.
- **Why scores are blended, not vectors:** liked notes live in note-only space and liked fragrances in a wider notes-and-accords space. The two cannot be added directly without inventing padding, so each side is scored against every candidate and the scores are combined.

## Evaluation

There is no answer key for what smells similar, so the checks avoid tuning against my own taste.

- **Negative control:** *Paper -* (Commodity), a fragrance I know I do not like and that shares no notes with the tuning or held-out fragrances, must never appear in recommendations. It does not.
- **Independent accord check:** note similarity is compared against accord overlap taken from Fragrantica's own tags, not from my similarity logic (Pearson correlation).
- **Held-out fragrances:** the blend was set using only *Libre* and *Idole*. *Carat* and *Baccarat Rouge 540* were kept aside to check generalisation.

| held-out fragrance | correlation with accord overlap |
|---|---|
| Carat | 0.84 |
| Baccarat Rouge 540 | 0.69 |

Generalisation is uneven, and I report it that way.

## Limitations

- **No ground truth:** alpha and the blend ratio were deliberately not tuned against what I already think is similar, because the test would only confirm my own taste. For the same reason precision at top-k was rejected as a metric.
- **Dupes of dupes:** querying a single well-known fragrance returns clone-house fragrances and their copies. The near-duplicate filter reduces this but does not remove it.
- **Spelling variants:** I merged 32 near-duplicate note spellings after checking each pair, but it is not possible to catch every variant in a scraped dataset.
- **Uneven generalisation:** see the held-out results above.
- **Saved history:** the "Saved" and "Scorecard" pages read `data/saved_history.json` on disk. On Streamlit Community Cloud this file may reset when the app restarts.
- **Scope:** this is a capstone project, not a production system. There is no usage monitoring and no refresh of the underlying data.

## Next steps

- **Collaborative filtering:** recommend from behaviour, what people with similar taste also liked, using the ratings, vote counts, and have/want data in the dataset. Not attempted in this project.
- **Rating-based plausibility check:** use that same data to check recommendations, asking whether top results also share similar ratings or have/want patterns.

## Run it locally

Deployed on Streamlit Community Cloud using Python 3.14. Dependencies are pinned in `requirements.txt`.

```
git clone https://github.com/nvalaa/Accordly
cd Accordly
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run home.py
```

To rebuild the fitted objects from the cleaned dataset (only needed if `data/perfumes_final.pkl` changes):

```
python prep_data.py
```

## Repository contents

| path | purpose |
|---|---|
| `home.py` | main app: search, recommendations, score breakdown |
| `pages/1_explained.py` | plain-language explanation of how the recommender works |
| `pages/2_saved.py` | saved fragrances, notes, and accords |
| `pages/3_scorecard.py` | summary of the most common saved notes and accords |
| `recommender.py` | shared recommendation logic |
| `prep_data.py` | rebuilds the fitted objects and records the note merges |
| `constants.py` | shared settings and colours |
| `explainer_diagrams.py` | diagrams for the Explained page |
| `data/` | cleaned dataset and fitted objects |
| `docs/` | presentation (PowerPoint and PDF) |

## Data

Scraped Fragrantica fragrance data downloaded from Kaggle (dataset name and link to be confirmed). Check the dataset's licence before reusing the data. Fragrance names, notes, and accords belong to their respective sources.
