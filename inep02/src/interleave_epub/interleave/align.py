"""Align to list of sentences."""

import json
from pathlib import Path

from loguru import logger as lg
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
        self.sim = cosine_similarity(enc_orig_src, enc_tran_dst)
        # TODO save the thing
