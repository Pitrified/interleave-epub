"""Align to list of sentences."""

import json
from pathlib import Path

from loguru import logger as lg
import numpy as np
from scipy.signal.windows import triang
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from interleave_epub.epub.chapter import Chapter
from interleave_epub.nlp.utils import sentence_encode_np


class Aligner:
    """Align to list of sentences."""

    def __init__(
        self,
        ch_src: Chapter,
        ch_dst: Chapter,
        sent_which_align: dict[str, str],
        ch_id_pair_str: str,
        lt_sent_tra: str,
        sent_transformer: SentenceTransformer,
        align_cache_fol: Path,
        force_align: bool = False,
    ) -> None:
        """Initialize the aligner."""
        self.ch_src = ch_src
        self.ch_dst = ch_dst
        self.sent_which_align = sent_which_align
        self.lt_sent_tra = lt_sent_tra
        self.sent_transformer = sent_transformer
        self.ch_id_pair_str = ch_id_pair_str
        self.align_cache_fol = align_cache_fol

        self.match_info_path = {}

        align_info_name = f"info_align_{self.ch_id_pair_str}.json"
        self.match_info_path["align"] = self.align_cache_fol / align_info_name
        sim_name = f"info_sim_{self.ch_id_pair_str}.npy"
        self.match_info_path["sim"] = self.align_cache_fol / sim_name

        # if we have an alignment already computed, load it
        # unless we are forcing a realignment
        if (
            not force_align
            and self.match_info_path["align"].exists()
            and self.match_info_path["sim"].exists()
        ):
            lg.info("Found match info at {}", self.match_info_path["align"])
            self.match_info = json.loads(self.match_info_path["align"].read_text())
            # TODO reload the things

    def compute_similarity(self):
        """Compute the similarity between the two list of sentences."""
        # encode the sentences
        enc_orig_src = sentence_encode_np(
            self.sent_transformer[self.lt_sent_tra],
            self.ch_src.sents_text[self.sent_which_align["src"]],
        )
        enc_tran_dst = sentence_encode_np(
            self.sent_transformer[self.lt_sent_tra],
            self.ch_dst.sents_text[self.sent_which_align["dst"]],
        )
        # compute the similarity
        self.sim: np.ndarray = cosine_similarity(enc_orig_src, enc_tran_dst)
        # TODO save the thing
        np.save(self.match_info_path["sim"], self.sim)

    def align_auto(
        self,
        win_len: int = 20,
        min_sent_len: int = 4,
    ):
        """Align the sentences using the similarity matrix.

        First use the matrix to fit a line,
        then refine with a triangular filter to give more weight to values near the line.
        """
        # length of the sentences in the two chapters
        sent_len_src = self.ch_src.sents_len[self.sent_which_align["src"]]
        sent_len_dst = self.ch_dst.sents_len[self.sent_which_align["dst"]]
        # number of sentences in the two chapters
        self.sent_num_src = self.ch_src.sents_num[self.sent_which_align["src"]]
        self.sent_num_dst = self.ch_dst.sents_num[self.sent_which_align["dst"]]
        self.ratio = self.sent_num_src / self.sent_num_dst

        #############################################################################
        # first iteration of matching: use the similarity matrix in a greedy way
        self.all_good_ids_src = []
        self.all_good_ids_dst_max = []

        # self.sim.shape = (sent_num_src, sent_num_dst)
        lg.debug(f"{self.sim.shape=} {self.sent_num_src=} {self.sent_num_dst=}")

        for id_src in range(self.sent_num_src):

            # the similarity of this src sent to all the translated ones
            # this_sent_sim.shape = (sent_num_dst, )
            this_sent_sim: np.ndarray = self.sim[id_src]

            # find the center rescaled, there are different number of sents in the two chapters
            id_dst_ratio = int(id_src / self.ratio)

            # the chopped similarity array
            win_left = max(0, id_dst_ratio - win_len)
            win_right = min(self.sent_num_dst, id_dst_ratio + win_len + 1)
            some_sent_sim = this_sent_sim[win_left:win_right]

            # the dst sent id with highest similarity
            id_dst_max = some_sent_sim.argmax() + win_left

            # only save the results if the docs are long enough
            if (
                sent_len_src[id_src] > min_sent_len
                and sent_len_dst[id_dst_max] > min_sent_len
            ):
                self.all_good_ids_src.append(id_src)
                self.all_good_ids_dst_max.append(id_dst_max)

        # fit a line on the good matches
        self.fit_coeff = np.polyfit(self.all_good_ids_src, self.all_good_ids_dst_max, 1)
        self.fit_func = np.poly1d(self.fit_coeff)

        #############################################################################
        # second iteration of matching: use the line to rescale the similarity

        # build a triangular filter to give more relevance to sentences close to the fit
        triang_height = 1
        triang_filt = triang(win_len * 4 + 1) * triang_height + (1 - triang_height)
        triang_center = win_len * 2 + 1

        # all_max_rescaled = []
        self.all_good_ids_src_rescaled = []
        self.all_good_ids_dst_max_rescaled = []

        # self.all_ids_src = []
        self.all_ids_src = list(range(self.sent_num_src))
        self.all_ids_dst_max = []
        self.last_good_id_dst_max = 0

        for id_src in range(self.sent_num_src):

            # the similarity of this english sent to all the translated ones
            this_sent_sim = self.sim[id_src]

            # find the center rescaled because there are different number of sent in the two chapters
            id_dst_ratio = int(id_src / self.ratio)

            # the chopped similarity array, centered on id_dst_ratio
            win_left = max(0, id_dst_ratio - win_len)
            win_right = min(self.sent_num_dst, id_dst_ratio + win_len + 1)
            some_sent_sim = this_sent_sim[win_left:win_right]

            # the fit along the line
            ii_fit = self.fit_func([id_src])[0]
            ii_fit = int(ii_fit)
            if ii_fit < 0:
                ii_fit = 0
            if ii_fit >= self.sent_num_dst:
                ii_fit = self.sent_num_dst - 1
            # print(f"{id_src=} {id_dst_ratio=} {ii_fit=}")

            # chop the filter, centering the apex on the fitted line ii_fit
            # the apex is in win_len*2+1
            # the similarity is centered on id_dst_ratio
            # the shifted filter is still win_len*2+1 long
            delta_ii_fit = id_dst_ratio - ii_fit
            filt_edge_left = triang_center + delta_ii_fit - win_len - 1
            filt_edge_right = triang_center + delta_ii_fit + win_len + 0
            triang_filt_shifted = triang_filt[filt_edge_left:filt_edge_right]

            # chop the filter as well, if the similarity is near the border
            if id_dst_ratio < win_len:
                triang_filt_chop = triang_filt_shifted[win_len - id_dst_ratio :]
            elif id_dst_ratio > self.sent_num_dst - (win_len + 1):
                left_edge = self.sent_num_dst - (win_len + 1)
                triang_filt_chop = triang_filt_shifted[: -(id_dst_ratio - left_edge)]
            else:
                triang_filt_chop = triang_filt_shifted

            # print( f"{id_src=} {id_dst_ratio=} {id_dst_ratio-win_len=} {id_dst_ratio+win_len+1=} {len(some_sent_sim)=} {len(triang_filt_chop)=}")
            assert len(triang_filt_chop) == len(some_sent_sim)

            # rescale the similarity
            sim_rescaled = some_sent_sim * triang_filt_chop

            # find the max similarity on the rescaled sim array
            id_dst_max_rescaled = sim_rescaled.argmax() + win_left
            # all_max_rescaled.append(id_dst_max_rescaled)

            # keep if both sents are long
            if (
                sent_len_src[id_src] > min_sent_len
                and sent_len_dst[id_dst_max] > min_sent_len
            ):
                self.all_good_ids_src_rescaled.append(id_src)
                self.all_good_ids_dst_max_rescaled.append(id_dst_max_rescaled)
                # update the last max we saw
                self.last_good_id_dst_max = id_dst_max_rescaled

            # save all matches id_src-max
            # self.all_ids_src.append(id_src)
            self.all_ids_dst_max.append(int(self.last_good_id_dst_max))

        # return self.all_ids_src, self.all_ids_dst_max

    def compute_ooo_ids(self):
        """Find the non monothonic ids_dst_max."""
        is_ooo_flattened = []
        for id_src, id_dst_max in zip(self.all_ids_src, self.all_ids_dst_max):
            # check to the left if you can
            if id_src > 0:
                ooo_left = id_dst_max < self.all_ids_dst_max[id_src - 1]
            else:
                ooo_left = False
            # check to the right if you can
            if id_src < len(self.all_ids_dst_max) - 1:
                ooo_right = id_dst_max > self.all_ids_dst_max[id_src + 1]
            else:
                ooo_right = False
            # if any side is ooo, mark it
            ooo = ooo_right or ooo_left
            # if ooo: lg.debug(f"{id_src} {id_dst_max}")
            is_ooo_flattened.append(ooo)
