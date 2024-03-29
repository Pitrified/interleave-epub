"""Read the model state and render the html pages."""

from flask import render_template
from loguru import logger as lg
import matplotlib.pyplot as plt

from interleave_epub.flask_app.utils import fig2imgb64str
from interleave_epub.interleave.constants import (
    lt_dst_default,
    lt_options,
    lt_src_default,
)
from interleave_epub.interleave.interactive import InterleaverInteractive
from interleave_epub.utils import is_index_valid, validate_index


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
    # extract the aligner for sanity
    al = ii.aligners[ii.ch_id_pair_str]

    # plot the similarity matrix
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_title(f"Similarity")
    ax.imshow(al.sim.T, origin="lower", aspect="auto")
    # ax.axvline(al.viz_id_src)
    # ax.axhline(al.viz_id_dst)
    sim_fig_str = fig2imgb64str(fig)

    # plot the alignment
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(al.all_good_ids_src, al.all_good_ids_dst_max, s=0.1)
    ax.plot([0, al.sent_num_src], [0, al.sent_num_dst], linewidth=0.3)
    fit_y = al.fit_func([0, al.sent_num_src])
    ax.plot([0, al.sent_num_src], fit_y)
    ax.plot(al.all_ids_src, al.all_ids_dst_max, linewidth=0.9)
    ax.set_title(f"Alignment")
    align_fig_str = fig2imgb64str(fig)

    # build the list of paired paragraphs to show
    pars_info: list[dict] = []
    for i in range(-al.viz_win_size, al.viz_win_size):

        valid_id_src, valid_id_dst = False, False

        # find the viz id of the src par to show
        viz_id_src_show = al.curr_fix_src_par_id + i
        # check if it is usable
        if is_index_valid(viz_id_src_show, al.ch_src.paragraphs):
            par_src_text = al.ch_src.paragraphs[viz_id_src_show].get_text()
            valid_id_src = True
            # the dst id we are currently matching this src par to
            guess_id_dst = al.better_par_src_to_dst_flat[viz_id_src_show]
        else:
            par_src_text = "-"
            guess_id_dst = 0

        # find the viz id of the dst par to show
        viz_id_dst_show = al.last_par_dst_id + i
        # check if it is usable
        if is_index_valid(viz_id_dst_show, al.ch_dst.paragraphs):
            par_dst_text = al.ch_dst.paragraphs[viz_id_dst_show].get_text()
            valid_id_dst = True
        else:
            par_dst_text = "-"

        # if both ids are not valid, do not visualize them
        if not valid_id_src and not valid_id_dst:
            continue

        pars_info.append(
            {
                "par_src_text": par_src_text,
                "par_dst_text": par_dst_text,
                "viz_id_src_show": viz_id_src_show,
                "viz_id_dst_show": viz_id_dst_show,
                "guess_id_dst": guess_id_dst,
            }
        )

    # dst par id of the par currently being aligned
    guess_id_dst_for_viz_id_src = al.better_par_src_to_dst_flat[al.curr_fix_src_par_id]

    return render_template(
        "align.html",
        src_lang="French",
        dst_lang="English",  # TODO
        pars_info=pars_info,
        viz_id_src=al.curr_fix_src_par_id,
        ch_id_src=ii.ch_id_src,
        ch_id_dst=ii.ch_id_dst,
        ch_first_id=ii.ch_first_id,
        ch_delta_id=ii.ch_delta_id,
        guess_id_dst_for_viz_id_src=guess_id_dst_for_viz_id_src,
        done_aligning=al.done_aligning,
        sim_fig_str=sim_fig_str,
        align_fig_str=align_fig_str,
    )


def render_align_old(ii: InterleaverInteractive):
    """Render the align page."""
    # extract the aligner for sanity
    al = ii.aligners[ii.ch_id_pair_str]

    # plot the similarity matrix
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_title(f"Similarity")
    ax.imshow(al.sim.T, origin="lower", aspect="auto")
    ax.axvline(al.viz_id_src)
    ax.axhline(al.viz_id_dst)
    sim_fig_str = fig2imgb64str(fig)

    # plot the alignment
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(al.all_good_ids_src, al.all_good_ids_dst_max, s=0.1)
    ax.plot([0, al.sent_num_src], [0, al.sent_num_dst], linewidth=0.3)
    fit_y = al.fit_func([0, al.sent_num_src])
    ax.plot([0, al.sent_num_src], fit_y)
    ax.plot(al.all_ids_src, al.all_ids_dst_max, linewidth=0.9)
    ax.set_title(f"Alignment")
    align_fig_str = fig2imgb64str(fig)

    # build the list of paired sentences to show
    sents_info: list[dict] = []
    for i in range(-al.viz_win_size, al.viz_win_size):

        valid_id_src, valid_id_dst = False, False

        # find the viz id of the src sentence to show
        viz_id_src_show = al.viz_id_src + i
        # check if it is usable
        if is_index_valid(viz_id_src_show, al.sents_text_src_viz):
            # get the corresponding sentence
            sent_text_src = al.sents_text_src_viz[viz_id_src_show]
            # get the current matching dst id we have for this src id
            # the actual matching, not the interpolated one
            # the interpolated one is used as center of the visualization for dst
            guess_id_dst = al.all_ids_dst_max[viz_id_src_show]
            valid_id_src = True
        else:
            sent_text_src = "-"
            guess_id_dst = 0

        # find the viz id of the dst sentence to show
        viz_id_dst_show = al.viz_id_dst + i
        # check if it is usable
        if is_index_valid(viz_id_dst_show, al.sents_text_dst_viz):
            # get the corresponding sentence
            sent_text_dst = al.sents_text_dst_viz[viz_id_dst_show]
            valid_id_dst = True
        else:
            sent_text_dst = "-"

        # if both ids are not valid, do not visualize them
        if not valid_id_src and not valid_id_dst:
            continue

        sents_info.append(
            {
                "sent_text_src": sent_text_src,
                "sent_text_dst": sent_text_dst,
                "viz_id_src_show": viz_id_src_show,
                "viz_id_dst_show": viz_id_dst_show,
                "guess_id_dst": guess_id_dst,
            }
        )

    guess_id_dst_for_viz_id_src = al.all_ids_dst_max[al.viz_id_src]

    return render_template(
        "align.html",
        src_lang="French",
        dst_lang="English",  # TODO
        sents_info=sents_info,
        viz_id_src=al.viz_id_src,
        ch_id_src=ii.ch_id_src,
        ch_id_dst=ii.ch_id_dst,
        ch_first_id=ii.ch_first_id,
        ch_delta_id=ii.ch_delta_id,
        guess_id_dst_for_viz_id_src=guess_id_dst_for_viz_id_src,
        sim_fig_str=sim_fig_str,
        align_fig_str=align_fig_str,
    )
