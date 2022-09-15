"""Interactive interleaver."""

import json
from pathlib import Path
from typing import IO, cast

from loguru import logger as lg
from sentence_transformers import SentenceTransformer
from transformers.pipelines import pipeline
from transformers.pipelines.text2text_generation import TranslationPipeline

from interleave_epub.epub.epub import EPub
from interleave_epub.interleave.align import Aligner
from interleave_epub.interleave.constants import (
    hug_model_name_tmpl,
    hug_trad_cache_fol,
    hug_trad_file_tmpl,
    sent_model_names,
    spa_model_cache_fol,
    spa_model_names,
)
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache
from interleave_epub.nlp.local_spacy_model import spacy_load_local_model
from interleave_epub.utils import get_package_fol, orig_or_trad, src_or_dst


class InterleaverInteractive:
    """Interactive interleaver.

    set the current chap being aligned
    alignment are cached somewhere
        - need a cache folder
        - need a button to ignore that
    """

    def __init__(self) -> None:
        """Initialize the interleaver."""
        # translate src/dst to language tags {'src': 'fr', 'dst': 'en'}
        self.sd_to_lt: dict[str, str] = {}
        self.has_both_lts = False

        # mark if the NLP models are loaded
        self.has_nlp_loaded = False

        # placeholder for the epubs
        self.epubs: dict[str, EPub] = {}
        self.has_both_epubs = False

    def set_lang_tag(self, lang_tag: str, which_lang: src_or_dst) -> None:
        """Set the lang tag for one of the books.

        self.sd_to_lt = {'src': 'en', 'dst': 'fr'}
        """
        self.sd_to_lt[which_lang] = lang_tag

        if "src" in self.sd_to_lt and "dst" in self.sd_to_lt:
            self.has_both_lts = True
            # list: ['en', 'fr']
            self.lts_l = list(self.sd_to_lt.values())
            # pair as tuple: [('en', 'fr'), ('fr', 'en')]
            self.lts_pt = list(zip(self.lts_l, self.lts_l[::-1]))
            # pair hyphen: ['en-fr', 'fr-en']
            self.lts_ph = [f"{l0}-{l1}" for l0, l1 in self.lts_pt]
            # swap the tags and src
            self.lt_to_sd = {v: k for k, v in self.sd_to_lt.items()}

    def load_nlp(self) -> None:
        """Add nlp things to the interleaver."""
        if self.has_nlp_loaded:
            return

        # load the spacy models
        self.nlp = {
            lt: spacy_load_local_model(spa_model_names[lt], spa_model_cache_fol)
            for lt in self.lts_l
        }
        lg.debug("Loaded SpaCy models.")

        # get the location of the trad cache files
        self.trad_cache_path = {
            lth: hug_trad_cache_fol / hug_trad_file_tmpl.format(lth)
            for lth in self.lts_ph
        }

        # MAYBE this should be settable?
        # definitely not hardcoded with a language tag lol
        load_pipe = {
            "fr-en": False,
            "en-fr": False,
        }

        # load the huggingface pipelines
        self.pipe = {
            lth: cast(
                TranslationPipeline,
                pipeline("translation", model=hug_model_name_tmpl.format(lth)),
            )
            if load_pipe[lth]
            else None
            for lth in self.lts_ph
        }

        # create the cached pipelines
        self.pipe_cache = {
            lth: TranslationPipelineCache(
                self.pipe[lth], self.trad_cache_path[lth], lt_pair=lth
            )
            for lth in self.lts_ph
        }

        # load the sentence transformer
        # TODO: should set which side to use src or dst
        # which will mean aligning src_trad-dst_orig or vice versa
        # we assume that dst is english and we know the sent model for that
        self.lt_sent_tra = self.sd_to_lt["dst"]
        # TODO: why on CPU? parametrize that
        self.sent_transformer = {
            self.lt_sent_tra: SentenceTransformer(
                sent_model_names[self.lt_sent_tra], device="cpu"
            )
        }
        # which sent to use to align in the source and dest ebook
        self.sent_which_align = {
            "src": "trad",
            "dst": "orig",
        }

        self.has_nlp_loaded = True

    def add_book(
        self,
        ep_path: str | IO[bytes] | Path,
        which_ep: src_or_dst,
        ep_name: str = "",
    ) -> None:
        """Add a book to the interleaver.

        Pass which one it is.
        """
        if not self.has_both_lts:
            return

        self.load_nlp()

        if which_ep == "src":
            lt_orig = self.sd_to_lt["src"]
            lt_trad = self.sd_to_lt["dst"]
        else:
            lt_orig = self.sd_to_lt["dst"]
            lt_trad = self.sd_to_lt["src"]

        # load the epub
        self.epubs[which_ep] = EPub(
            ep_path,
            ep_name,
            lt_orig,
            lt_trad,
            self.nlp,
            self.pipe_cache,
        )

        if "src" in self.epubs and "dst" in self.epubs:
            self.has_both_epubs = True
            # chapter we are currently fixing
            self.ch_curr_id = 0
            # id of the first chapter in the src book
            self.ch_first = 0
            # delta between src and dst chapter ids
            self.ch_delta = 0

    def create_temp_fol(self) -> None:
        """Create the temp folder this pair of books.

        If it exists, do NOT overwrite that: we might have already aligned some chapters.
        """
        # base cache folder for all alignment
        cache_fol = get_package_fol(which_fol="align_cache")

        # create a folder for this pair of books, removing spaces
        pair_name = "_".join([f"{s.epub_name[:20]}" for s in self.epubs.values()])
        pair_name = "".join(pair_name.split())
        self.align_cache_fol = cache_fol / pair_name
        if not self.align_cache_fol.exists():
            self.align_cache_fol.mkdir(parents=True)

    def align_auto(self, force_align: bool = False) -> None:
        """Compute the similarity and hopeful alignment.

        TODO: Whenever a change in ch_curr/ch_delta occurs, this is called.
        """
        if not self.has_both_epubs:
            lg.warning("Load both epubs before aligning.")
            return

        # create a folder for temporary files
        self.create_temp_fol()

        # get the ids of the chapters in src and dst book
        ch_id_src = self.ch_curr_id + self.ch_first
        ch_id_dst = ch_id_src + self.ch_delta

        # where to save the WIP alignment info
        ch_id_pair_str = f"{ch_id_src}_{ch_id_dst}"

        # extract the current chapters we are using
        ch_curr_src = self.epubs["src"].chapters[ch_id_src]
        ch_curr_dst = self.epubs["dst"].chapters[ch_id_dst]

        self.aligner = Aligner(
            ch_curr_src,
            ch_curr_dst,
            self.sent_which_align,
            ch_id_pair_str,
            self.lt_sent_tra,
            self.sent_transformer,
            self.align_cache_fol,
        )

    def change_chapter(self) -> None:
        """Go and fix the next chapter."""

    def change_chapter_delta(self) -> None:
        """Change the delta between chapters. Also set which is the first."""

    def select_src_sent(self) -> None:
        """Select a new src sent to align."""

    def pick_dst_sent(self) -> None:
        """Pick which dst sent is the right one for the currently selected src."""

    def scroll_sent(self, which_sents, direction) -> None:
        """Scroll the right bunch of sentences in the right direction."""
