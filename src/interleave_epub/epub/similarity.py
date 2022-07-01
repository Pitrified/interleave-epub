"""Similarity matching of sentences and related functions."""


from matplotlib import pyplot as plt
import numpy as np
from scipy.signal.windows import triang

from interleave_epub.epub.chapter import Chapter


def match_similarity(
    sim: np.ndarray,
    # chap_src: Chapter,
    # chap_dst: Chapter,
    sents_len_src_orig,
    sents_len_dst_tran,
    win_len: int = 20,
):
    """Compute the matches between sentences in the two chapters."""
    # number of sentences in the two chapters
    # sent_num_src = chap_src.sents_num
    # sent_num_dst = chap_dst.sents_num
    sent_num_src = len(sents_len_src_orig)
    sent_num_dst = len(sents_len_dst_tran)
    ratio = sent_num_src / sent_num_dst

    # first iteration of matching
    all_good_max = []
    all_good_i = []

    for i in range(sent_num_src):

        # the similarity of this src sent to all the translated ones
        this_sent_sim = sim[i]

        # find the center rescaled because there are different number of sents in the two chapters
        ii = int(i / ratio)

        # the chopped similarity array
        win_left = max(0, ii - win_len)
        win_right = min(sent_num_dst, ii + win_len + 1)
        some_sent_sim = this_sent_sim[win_left:win_right]

        # the dst sent id with highest similarity
        max_id = some_sent_sim.argmax() + win_left

        # only save the results if the docs are long enough
        if (
            # len(chap_src.sents_doc_orig[i]) > 4
            # and len(chap_dst.sents_doc_tran[max_id]) > 4
            sents_len_src_orig[i] > 4
            and sents_len_dst_tran[max_id] > 4
        ):
            all_good_i.append(i)
            all_good_max.append(max_id)

    # fit a line on the matches
    fit_coeff = np.polyfit(all_good_i, all_good_max, 1)
    fit_func = np.poly1d(fit_coeff)

    # build a triangular filter to give more relevance to sentences close to the fit
    triang_height = 1
    triang_filt = triang(win_len * 4 + 1) * triang_height + (1 - triang_height)
    triang_center = win_len * 2 + 1

    all_max_rescaled = []
    all_good_i_rescaled = []
    all_good_max_rescaled = []

    all_i = []
    all_max_flattened = []
    last_max = 0

    for i in range(sent_num_src):

        # the similarity of this english sent to all the translated ones
        this_sent_sim = sim[i]

        # find the center rescaled because there are different number of sent in the two chapters
        ii = int(i / ratio)

        # the chopped similarity array, centered on ii
        win_left = max(0, ii - win_len)
        win_right = min(sent_num_dst, ii + win_len + 1)
        some_sent_sim = this_sent_sim[win_left:win_right]

        # the fit along the line
        ii_fit = fit_func([i])[0]
        ii_fit = int(ii_fit)
        if ii_fit < 0:
            ii_fit = 0
        if ii_fit >= sent_num_dst:
            ii_fit = sent_num_dst - 1
        # print(f"{i=} {ii=} {ii_fit=}")

        # chop the filter, centering the apex on the fitted line ii_fit
        # the apex is in win_len*2+1
        # the similarity is centered on ii
        # the shifted filter is still win_len*2+1 long
        delta_ii_fit = ii - ii_fit
        filt_edge_left = triang_center + delta_ii_fit - win_len - 1
        filt_edge_right = triang_center + delta_ii_fit + win_len + 0
        triang_filt_shifted = triang_filt[filt_edge_left:filt_edge_right]

        # chop the filter as well, if the similarity is near the border
        if ii < win_len:
            triang_filt_chop = triang_filt_shifted[win_len - ii :]
        elif ii > sent_num_dst - (win_len + 1):
            left_edge = sent_num_dst - (win_len + 1)
            triang_filt_chop = triang_filt_shifted[: -(ii - left_edge)]
        else:
            triang_filt_chop = triang_filt_shifted

        # print( f"{i=} {ii=} {ii-win_len=} {ii+win_len+1=} {len(some_sent_sim)=} {len(triang_filt_chop)=}")
        assert len(triang_filt_chop) == len(some_sent_sim)

        # rescale the similarity
        sim_rescaled = some_sent_sim * triang_filt_chop

        # find the max similarity on the rescaled sim array
        max_id_rescaled = sim_rescaled.argmax() + win_left
        all_max_rescaled.append(max_id_rescaled)

        # keep if both sents are long
        if (
            # len(chap_src.sents_doc_orig[i]) > 4
            # and len(chap_dst.sents_doc_tran[max_id_rescaled]) > 4
            sents_len_src_orig[i] > 4
            and sents_len_dst_tran[max_id_rescaled] > 4
        ):
            all_good_i_rescaled.append(i)
            all_good_max_rescaled.append(max_id_rescaled)
            # update the last max we saw
            last_max = max_id_rescaled

        # save all matches i-max
        all_i.append(i)
        all_max_flattened.append(last_max)

    fig, ax = plt.subplots()
    ax.scatter(all_good_i, all_good_max, s=0.1)
    ax.plot([0, sent_num_src], [0, sent_num_dst], linewidth=0.3)
    fit_y = fit_func([0, sent_num_src])
    ax.plot([0, sent_num_src], fit_y)
    # ax.plot(all_good_i_rescaled, all_good_max_rescaled, linewidth=0.9)
    ax.plot(all_i, all_max_flattened, linewidth=0.9)
    ax.set_title(f"Matching")
    # ax.set_ylabel("")
    # ax.set_xlabel("")
    # st.pyplot(fig)

    return fig, all_i, all_max_flattened
