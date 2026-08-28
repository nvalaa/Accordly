"""
Shared diagram-building functions for explaining how config6 scores
fragrances. Designed to be imported from both the Streamlit app
(pages/1_explained.py) and, later, a notebook cell, so the same
explanation visuals are available in both places without duplicating code.

Two kinds of output:
  - HTML/CSS diagrams (returned as a raw HTML string) for conceptual,
    non-numeric illustrations, e.g. highlighting overlapping notes between
    two fragrances.
  - Plotly figures for anything with actual numbers, e.g. comparing note
    weights or similarity scores.

In Streamlit, render the HTML functions with:
    st.markdown(some_html_function(...), unsafe_allow_html=True)
and the plotly functions with:
    st.plotly_chart(some_figure_function(...), use_container_width=True)

In a notebook, render the HTML functions with:
    from IPython.display import HTML
    HTML(some_html_function(...))
and the plotly functions just by calling them directly (Jupyter renders a
returned plotly Figure automatically).
"""

import plotly.graph_objects as go

# Colours are passed in by the caller (matching the app's constants.py),
# rather than imported directly, so this module has no dependency on the
# Streamlit app's constants and can be reused in a notebook with its own
# palette if needed.


def notes_overlap_html(fragrance_a_name, fragrance_a_notes, fragrance_b_name,
                        fragrance_b_notes, card_bg, card_text, accent):
    """Two side-by-side note lists with shared notes highlighted, showing
    visually what "note overlap" means before any maths is introduced.
    """
    notes_a = set(fragrance_a_notes)
    notes_b = set(fragrance_b_notes)
    shared = notes_a & notes_b

    def render_list(notes, shared_set):
        items = ""
        for note in notes:
            is_shared = note in shared_set
            bg = accent if is_shared else "transparent"
            weight = "600" if is_shared else "400"
            items += (
                f'<div style="padding:4px 8px; margin:2px 0; border-radius:4px; '
                f'background:{bg}; font-weight:{weight};">{note}</div>'
            )
        return items

    return f"""
    <div style="background:{card_bg}; color:{card_text}; padding:16px; border-radius:8px;">
        <div style="display:flex; gap:24px;">
            <div style="flex:1;">
                <div style="font-weight:600; margin-bottom:8px;">{fragrance_a_name}</div>
                {render_list(fragrance_a_notes, shared)}
            </div>
            <div style="flex:1;">
                <div style="font-weight:600; margin-bottom:8px;">{fragrance_b_name}</div>
                {render_list(fragrance_b_notes, shared)}
            </div>
        </div>
        <div style="margin-top:8px;">
            Shared notes (highlighted): {', '.join(sorted(shared)) if shared else 'none'}
        </div>
    </div>
    """


def rarity_weighting_bar(common_note, common_note_weight, rare_note,
                          rare_note_weight, bar_colour, text_colour):
    """A simple two-bar plotly chart showing that a rare note counts for
    more than a common one, illustrating IDF weighting without formulas.
    """
    fig = go.Figure(
        data=[
            go.Bar(
                x=[common_note, rare_note],
                y=[common_note_weight, rare_note_weight],
                marker_color=bar_colour,
                text=[f"{common_note_weight:.2f}", f"{rare_note_weight:.2f}"],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="How much a shared note counts, based on how common it is",
        yaxis_title="Weight given to this note",
        font_color=text_colour,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def alpha_blend_chart(alphas, combined_scores, top_names, alpha, bar_colour,
                       accent_colour, text_colour):
    """Shows how the top-ranked result's combined score changes as alpha
    shifts weight between notes similarity and perfumes similarity.

    Each bar is a genuinely separate query at that alpha value, not the
    same fixed pair of scores re-blended: changing alpha can change which
    fragrance ranks #1 entirely, so top_names (shown as hover text) may
    differ from bar to bar, which is the actual, honest behaviour of the
    real recommender, not a simplification of it.
    """
    colours = [accent_colour if abs(a - alpha) < 0.01 else bar_colour for a in alphas]

    fig = go.Figure(
        data=[
            go.Bar(
                x=[str(round(a, 2)) for a in alphas],
                y=combined_scores,
                marker_color=colours,
                text=[f"{c:.2f}" for c in combined_scores],
                textposition="outside",
                customdata=top_names,
                hovertemplate="alpha=%{x}<br>combined score=%{y:.2f}<br>top result: %{customdata}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="How the top result's combined score changes as the notes/perfumes balance shifts",
        xaxis_title="Alpha (0 = perfumes only, 1 = notes only)",
        yaxis_title="Combined score",
        font_color=text_colour,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig
