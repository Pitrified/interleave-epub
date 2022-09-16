"""Read the model state and render the html pages."""

from flask import render_template
import matplotlib.pyplot as plt

from interleave_epub.flask_app.utils import fig2imgb64str
from interleave_epub.interleave.constants import (
    lt_dst_default,
    lt_options,
    lt_src_default,
)
from interleave_epub.interleave.interactive import InterleaverInteractive


def render_load():
    """Render the load page."""
    return render_template(
        "load.html",
        lts_list=lt_options,
        lt_src_default=lt_src_default,
        lt_dst_default=lt_dst_default,
    )


def render_align(ii: InterleaverInteractive):
    """Render the align page."""
    # plot the similarity matrix
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.imshow(ii.aligner.sim.T, origin="lower", aspect="auto")
    ax.set_title(f"Similarity")
    sim_fig_str = fig2imgb64str(fig)

    # plot the alignment
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(ii.aligner.all_good_ids_src, ii.aligner.all_good_ids_dst_max, s=0.1)
    ax.plot([0, ii.aligner.sent_num_src], [0, ii.aligner.sent_num_dst], linewidth=0.3)
    fit_y = ii.aligner.fit_func([0, ii.aligner.sent_num_src])
    ax.plot([0, ii.aligner.sent_num_src], fit_y)
    ax.plot(ii.aligner.all_ids_src, ii.aligner.all_ids_dst_max, linewidth=0.9)
    ax.set_title(f"Alignment")
    align_fig_str = fig2imgb64str(fig)

    return render_template(
        "align.html",
        sim_fig_str=sim_fig_str,
        align_fig_str=align_fig_str,
    )
