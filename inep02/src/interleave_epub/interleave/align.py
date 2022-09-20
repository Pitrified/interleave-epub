"""Align to list of sentences."""

from collections import Counter
from itertools import groupby
import json
from math import isnan
from pathlib import Path
from timeit import default_timer

from loguru import logger as lg
import numpy as np
import pandas as pd
from scipy.signal.windows import triang
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from interleave_epub.epub.chapter import Chapter
from interleave_epub.nlp.utils import sentence_encode_np
from interleave_epub.utils import are_contiguos


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
        viz_win_size: int = 10,
    ) -> None:
        """Initialize the aligner."""
        self.ch_src = ch_src
        self.ch_dst = ch_dst
        self.sent_which_align = sent_which_align
        self.lt_sent_tra = lt_sent_tra
        self.sent_transformer = sent_transformer
        self.ch_id_pair_str = ch_id_pair_str
        self.align_cache_fol = align_cache_fol
        self.viz_win_size = viz_win_size

        # extract the right list of sentences to use when computing the similarity
        self.sents_text_src_align = self.ch_src.sents_text[self.sent_which_align["src"]]
        self.sents_text_dst_align = self.ch_dst.sents_text[self.sent_which_align["dst"]]
        # extract the original text to visualize
        self.sents_text_src_viz = self.ch_src.sents_text["orig"]
        self.sents_text_dst_viz = self.ch_dst.sents_text["orig"]

        # the paths of the cached info
        self.match_info_path: dict[str, Path] = {}
        align_info_name = f"info_align_{self.ch_id_pair_str}.json"
        self.match_info_path["align"] = self.align_cache_fol / align_info_name
        sim_name = f"info_sim_{self.ch_id_pair_str}.npy"
        self.match_info_path["sim"] = self.align_cache_fol / sim_name

        # use cached res if force align is false and all the paths exist
        use_cached_res = (
            not force_align
            and self.match_info_path["align"].exists()
            and self.match_info_path["sim"].exists()
        )

        # TODO some checks on consistency of cached alignment info

        # compute the alignment even if we have a cached version,
        # we want all the other class variables to be set

        if use_cached_res:
            self.sim = np.load(self.match_info_path["sim"])
        else:
            self.compute_sentence_similarity()
            # save the similarity
            np.save(self.match_info_path["sim"], self.sim)

        self.align_sentences()

        # # if we have an alignment already computed, load it
        # # unless we are forcing a realignment
        # # the only thing we change are the matching dst ids
        # if use_cached_res:
        #     lg.info("Found match info at {}", self.match_info_path["align"])
        #     align_info = json.loads(self.match_info_path["align"].read_text())
        #     self.all_ids_dst_max: list[int] = align_info["all_ids_dst_max"]
        #     # TODO reload fixed_src_ids as well?

        # use the possibly updated matching to compute ooo ids
        self.compute_ooo_ids()
        self.interpolate_ooo_ids()

        # align the paragraphs
        self.align_paragraphs()

        # reload the partial paragraph matches
        if use_cached_res:
            lg.info("Found match info at {}", self.match_info_path["align"])
            align_info = json.loads(self.match_info_path["align"].read_text())
            tmp: dict[int, int] = align_info["better_par_src_to_dst_flat"]
            # json files treat keys as string
            self.better_par_src_to_dst_flat = {int(k): v for k, v in tmp.items()}
        else:
            # if you are not reloading, save the initial match
            # or next time the use_cached_res will still be false
            # (the first time there is no partial file until you set the first par)
            self.save_align_state()

        # find valid ooo paragraphs to fix manually
        # src ids we have set manually, to be skipped when searching for ooo ids
        self.fixed_src_par_ids: list[int] = []
        self.find_next_par_to_fix()

        self.done_aligning = False

        # # set up the interactive parts of the Aligner
        # # src ids we have set manually, to be skipped when searching for ooo ids
        self.fixed_ids_src: list[int] = []
        # self.find_next_valid_ooo()

    def compute_sentence_similarity(self):
        """Compute the similarity between the two list of sentences."""
        lg.debug(f"Computing similarity.")
        t0 = default_timer()
        # encode the sentences
        enc_orig_src = sentence_encode_np(
            self.sent_transformer[self.lt_sent_tra], self.sents_text_src_align
        )
        enc_tran_dst = sentence_encode_np(
            self.sent_transformer[self.lt_sent_tra], self.sents_text_dst_align
        )
        # compute the similarity
        self.sim: np.ndarray = cosine_similarity(enc_orig_src, enc_tran_dst)
        lg.debug(f"Computing similarity: done in {default_timer()-t0:.2f}s.")

    def align_sentences(
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
            # lg.debug(f"{id_src=} {id_dst_ratio=} {ii_fit=}")

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

            # lg.debug( f"{id_src=} {id_dst_ratio=} {id_dst_ratio-win_len=} {id_dst_ratio+win_len+1=} {len(some_sent_sim)=} {len(triang_filt_chop)=}")
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

    def compute_ooo_ids(self):
        """Find the non monothonic ids_dst_max."""
        self.is_ooo_flattened = []
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
            self.is_ooo_flattened.append(ooo)

    def interpolate_ooo_ids(self):
        """Remove the ooo matches and interpolate them.

        These will be the first guess used to present the paragraph options to the user.
        """
        # interpolate the values for the ooo guesses
        self.all_ids_dst_interpolate = pd.Series(self.all_ids_dst_max)
        self.all_ids_dst_interpolate[self.is_ooo_flattened] = np.nan
        self.all_ids_dst_interpolate.interpolate(inplace=True)

        # pair up src and dst interpolated cs_ids
        self.interp_cs_src_to_dst = {
            cs_src: cs_dst
            for cs_src, cs_dst in zip(
                self.all_ids_src,
                self.all_ids_dst_interpolate,
            )
        }

    def align_paragraphs(self):
        """Align the paragraphs using the sentence alignment."""
        # the fraction of sentences in a src paragraph
        # matched to the same dst paragraph to have a direct match
        self.th_consensus = 0.6

        # pair up good (long) sentences id in the chapter and the paragraph id they belong to
        cs_p_src_ids = [
            {
                "cs_src_id": cs_src_id,
                "par_src_id": self.ch_src.cs_to_ps[cs_src_id][0],
            }
            for cs_src_id in self.all_good_ids_src_rescaled
        ]

        ############################################################
        # the first paragraph matching
        self.good_par_src_to_dst = {}

        # group the pairs on the paragraphs
        # par_src_id: the src paragraph
        # cs_p_src_par_ids: the (src_chap_sent_id, src_par_id) pairs for this src_paragraph
        for par_src_id, cs_p_src_par_ids in groupby(
            cs_p_src_ids, lambda x: x["par_src_id"]
        ):

            # the src chapter sentence ids for this src paragraph
            cs_src_ids = list(cs_p_src["cs_src_id"] for cs_p_src in cs_p_src_par_ids)
            num_sents_src = len(cs_src_ids)
            # lg.debug("{} {} {}", par_src_id, cs_src_ids, num_sents_src)

            # search for the cs_p_src id in the good_src_rescaled dict
            # if you find it, get the corresponding dst cs_src_id
            # -> we are iterating over the all_good_ids_src_rescaled sooo
            # extract all the paragraphs those sentences belong to
            par_dst_ids = []
            for cs_src_id in cs_src_ids:
                if cs_src_id in self.interp_cs_src_to_dst:
                    # the chapter_sentence_dst id
                    cs_dst_id = self.interp_cs_src_to_dst[cs_src_id]
                    # the interpolated values are not int
                    cs_dst_id = int(cs_dst_id)
                    # dst (paragraph, ps) id
                    ps_dst_id = self.ch_dst.cs_to_ps[cs_dst_id]
                    # get only the paragraph
                    par_dst_ids.append(ps_dst_id[0])
                else:
                    lg.warning(f"Very unexpected, missing {cs_src_id}.")

            # decide if there is a consensus on the paragraphs
            par_dst_ids_count = Counter(par_dst_ids)
            # lg.debug(f"\t{par_dst_ids_count}")
            par_dst_mc = par_dst_ids_count.most_common()[0]
            par_dst_mc_id = par_dst_mc[0]
            par_dst_mc_count = par_dst_mc[1]

            # if enough sentences point to the same dst paragraph, select that
            if par_dst_mc_count / num_sents_src > self.th_consensus:
                # lg.debug(f"\tMatching par {par_src_id} {par_dst_mc_id}")
                self.good_par_src_to_dst[par_src_id] = par_dst_mc_id
            else:
                # lg.debug(f"\tNo consensus matching. ------------------------")
                # if all the dst paragraphs are contiguos, select the min
                if are_contiguos(par_dst_ids):
                    self.good_par_src_to_dst[par_src_id] = min(par_dst_ids)
                    # lg.debug(f"\tContiguos matching {min(par_dst_ids)}.")
                # else: lg.debug(f"\tNo matching.")

        ############################################################
        # the second paragraph matching
        # if there are one or two paragraph missing from both src and dst
        # fill them in
        self.better_par_src_to_dst = {}
        # lg.debug("Building better_par_src_to_dst")

        last_src_id = 0
        last_dst_id = 0
        for par_src_id, par_dst_id in self.good_par_src_to_dst.items():
            # lg.debug(f"{par_src_id} {par_dst_id}")
            # if par_src_id > last_src_id + 1: lg.debug(f"missing src from {last_src_id+1} to {par_src_id-1}")

            after_last_par_src_id = last_src_id + 1
            after_last_par_dst_id = last_dst_id + 1
            prev_par_src_id = par_src_id - 1
            prev_par_dst_id = par_dst_id - 1

            # add the middle one if exactly one is missing
            if (
                after_last_par_src_id == prev_par_src_id
                and after_last_par_dst_id == prev_par_dst_id
            ):
                # lg.debug(f"probable {prev_par_src_id} {after_last_par_dst_id}")
                self.better_par_src_to_dst[prev_par_src_id] = after_last_par_dst_id

            # add the middle two if exactly two are missing
            elif (
                after_last_par_src_id + 1 == prev_par_src_id
                and after_last_par_dst_id + 1 == prev_par_dst_id
            ):
                # lg.debug( f"probable two {after_last_par_src_id} {after_last_par_dst_id}")
                # lg.debug( f"probable two {after_last_par_src_id+1} {after_last_par_dst_id+1}")
                self.better_par_src_to_dst[
                    after_last_par_src_id
                ] = after_last_par_dst_id
                self.better_par_src_to_dst[after_last_par_src_id + 1] = (
                    after_last_par_dst_id + 1
                )

            # add the current one
            self.better_par_src_to_dst[par_src_id] = par_dst_id

            # update data
            last_src_id = par_src_id
            last_dst_id = par_dst_id

        # flatten the better matching to have all the possible par src id
        self.better_par_src_to_dst_flat = {}
        for par_src_id in range(len(self.ch_src.paragraphs)):
            if par_src_id in self.better_par_src_to_dst:
                self.better_par_src_to_dst_flat[
                    par_src_id
                ] = self.better_par_src_to_dst[par_src_id]
            else:
                self.better_par_src_to_dst_flat[par_src_id] = -1

    def find_next_par_to_fix(self):
        """Find the first ooo src id that has not been fixed yet."""
        # self.is_ooo_par_flat = []
        self.last_par_dst_id = 0
        for par_src_id, par_dst_id in self.better_par_src_to_dst_flat.items():
            # lg.debug(f"flat {par_src_id} {par_dst_id}")
            # check to the left if you can
            if par_src_id > 0:
                ooo_left = par_dst_id < self.better_par_src_to_dst_flat[par_src_id - 1]
            else:
                ooo_left = False
            # check to the right if you can
            if par_src_id < len(self.better_par_src_to_dst_flat) - 1:
                ooo_right = par_dst_id > self.better_par_src_to_dst_flat[par_src_id + 1]
            else:
                ooo_right = False
            # if any side is ooo, mark it
            ooo = ooo_right or ooo_left
            if ooo:
                # lg.debug(f"ooo  {par_src_id} {par_dst_id}")
                if par_src_id not in self.fixed_src_par_ids:
                    self.curr_fix_src_par_id = par_src_id
                    self.curr_fix_dst_par_id = par_dst_id
                    # last_par_dst_id is magically the *previous* dst id
                    # and we'll use it to center the dst paragraph list
                    # as the current one might very well be wrong ooo one
                    return
            self.last_par_dst_id = par_dst_id
            # self.is_ooo_par_flat.append(ooo)

        # if no ooo was found, set all to 0
        lg.debug("Done aligning.")
        self.curr_fix_src_par_id = 0
        self.curr_fix_dst_par_id = 0
        self.last_par_dst_id = 0
        self.done_aligning = True

        # last_src_id = 0
        # last_dst_id = 0
        # for par_src_id, par_dst_id in self.better_par_src_to_dst_flat.items():
        #     lg.debug(f"{par_src_id} {par_dst_id}")
        #     # if we already manually aligned this paragraph, skip it
        #     if par_src_id in self.fixed_src_par_ids:
        #         continue
        #     # check for missing data
        #     if par_dst_id == -1:
        #         self.curr_fix_src_par_id = par_src_id
        #         self.curr_fix_dst_par_id = last_dst_id
        #         return
        #     # check for unsorted dst paragraphs
        #     if par_dst_id < last_dst_id:
        #         lg.debug("OOO paragraphs")
        #         self.curr_fix_src_par_id = last_src_id
        #         self.curr_fix_dst_par_id = last_dst_id
        #         return
        #     # update data
        #     last_src_id = par_src_id
        #     last_dst_id = par_dst_id

    def find_next_valid_ooo(self):
        """Find the first ooo src id that has not been fixed yet."""
        # find the first ooo src id
        is_ooo = self.is_ooo_flattened.copy()
        for fixed_id_src in self.fixed_ids_src:
            is_ooo[fixed_id_src] = False
        if True in is_ooo:
            self.curr_id_src = is_ooo.index(True)
        else:
            self.curr_id_src = 0
            lg.info(f"Finished aligning.")

        # update the best guess for dst id
        id_dst_interpolate_maybe = self.all_ids_dst_interpolate[self.curr_id_src]
        if isnan(id_dst_interpolate_maybe):
            lg.warning(f"{self.curr_id_src=} {id_dst_interpolate_maybe=} is nan")
            self.curr_id_dst_interpolate = 0
        else:
            self.curr_id_dst_interpolate = int(id_dst_interpolate_maybe)

        # reset src/dst viz ids
        self.viz_id_src = self.curr_id_src
        self.viz_id_dst = self.curr_id_dst_interpolate

    def save_align_state(self):
        """Write the current alignment state."""
        align_info = {
            "all_ids_dst_max": self.all_ids_dst_max,
            "better_par_src_to_dst_flat": self.better_par_src_to_dst_flat,
        }
        self.match_info_path["align"].write_text(json.dumps(align_info, indent=4))

    def pick_dst_sent(self, id_dst_correct: int) -> None:
        """Pick which dst sent is the right one for the currently selected src."""
        # save the correct dst id
        self.all_ids_dst_max[self.curr_id_src] = id_dst_correct
        # save the intermediate result
        self.save_align_state()
        # mark this src id as fixed manually
        self.fixed_ids_src.append(self.curr_id_src)
        # compute the remaining ooo ids with the new matching
        self.compute_ooo_ids()
        # find the next src id to fix
        self.find_next_valid_ooo()

    def pick_dst_par(self, id_dst_correct: int) -> None:
        """Pick which dst par is the right one for the currently selected src."""
        # save the correct dst id
        self.better_par_src_to_dst_flat[self.curr_fix_src_par_id] = id_dst_correct
        # save the intermediate result
        self.save_align_state()
        # mark this src id as fixed manually
        self.fixed_src_par_ids.append(self.curr_fix_src_par_id)
        # find the next src id to fix
        self.find_next_par_to_fix()

    def scroll_sent(self, which_sents, direction) -> None:
        """Scroll the right bunch of sentences in the right direction."""
