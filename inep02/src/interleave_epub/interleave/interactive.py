"""Interactive interleaver."""

from pathlib import Path
from typing import IO, cast

from loguru import logger as lg
from sentence_transformers import SentenceTransformer
from transformers.pipelines import pipeline
from transformers.pipelines.text2text_generation import TranslationPipeline

from interleave_epub.epub.epub import EPub
from interleave_epub.epub.epub_builder import EpubBuilder
from interleave_epub.interleave.align import Aligner
from interleave_epub.interleave.build_chap import interleave_chap
from interleave_epub.interleave.constants import (
    hug_model_name_tmpl,
    hug_model_names,
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
        self.epubs: dict[src_or_dst, EPub] = {}
        self.has_both_epubs = False

        # aligners
        self.aligners: dict[str, Aligner] = {}
        self.reset_chapter_ids()

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
        lg.debug("Loading NLP tools.")

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
            # "fr-en": True,
            # "en-fr": True,
            self.lts_ph[0]: True,
            self.lts_ph[1]: False,
        }

        # load the huggingface pipelines
        self.pipe = {
            lth: cast(
                TranslationPipeline,
                # pipeline("translation", model=hug_model_name_tmpl.format(lth)),
                pipeline("translation", model=hug_model_names[lth]),
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
        lg.debug("Loaded HuggingFace models.")

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
        lg.debug("Loaded SentenceTransformer model.")

        self.has_nlp_loaded = True

    def add_book(
        self,
        ep_path: str | IO[bytes] | Path,
        which_ep: src_or_dst,
        ep_name: str = "",
        ep_author: str = "",
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
        lg.debug(f"Loading {lt_orig} book.")
        self.epubs[which_ep] = EPub(
            ep_path,
            ep_name,
            ep_author,
            lt_orig,
            lt_trad,
            self.nlp,
            self.pipe_cache,
        )

        if "src" in self.epubs and "dst" in self.epubs:
            self.has_both_epubs = True

    def create_temp_fol(self) -> None:
        """Create the temp folder this pair of books.

        If it exists, do NOT overwrite that: we might have already aligned some chapters.
        """
        # create a name for this pair of books, removing spaces
        pair_name = "_".join([f"{s.epub_name[:20]}" for s in self.epubs.values()])
        pair_name = "".join(pair_name.split())

        # base cache folder for all alignment
        cache_fol = get_package_fol(which_fol="align_cache")
        # folder for this book alignment info
        self.align_cache_fol = cache_fol / pair_name
        if not self.align_cache_fol.exists():
            self.align_cache_fol.mkdir(parents=True)

        # base output folder for all books
        # TODO frankly don't know why it should be different from align_cache
        output_fol_root = get_package_fol("output_cache_fol")
        self.output_fol = output_fol_root / pair_name
        if not self.output_fol.exists():
            self.output_fol.mkdir(parents=True)

    def align_auto(self, force_align: bool = False) -> None:
        """Compute the similarity and hopeful alignment.

        TODO: Whenever a change in ch_curr/ch_delta occurs, this is called.
        """
        if not self.has_both_epubs:
            lg.warning("Load both epubs before aligning.")
            # TODO should return a specific code to signal the need to redirect back
            return

        # create a folder for temporary files
        self.create_temp_fol()

        # get the current chapters we are using and
        # create the aligner for this pair of chapters if needed
        if self.ch_id_pair_str not in self.aligners or force_align:
            self.aligners[self.ch_id_pair_str] = Aligner(
                self.epubs["src"].chapters[self.ch_id_src],
                self.epubs["dst"].chapters[self.ch_id_dst],
                self.sent_which_align,
                self.ch_id_pair_str,
                self.lt_sent_tra,
                self.sent_transformer,
                self.align_cache_fol,
                force_align,
            )

    def reset_chapter_ids(self) -> None:
        """Reset the chapter ids."""
        # chapter we are currently fixing
        self.ch_curr_id = 0
        # id of the first chapter in the src book
        self.ch_first_id = 0
        # delta between src and dst chapter ids
        self.ch_delta_id = 0
        self.update_chapter_id_info()

    def update_chapter_id_info(self) -> None:
        """Update the chapter id related variables."""
        # actual ids of the chapters in src and dst book
        self.ch_id_src = self.ch_curr_id + self.ch_first_id
        self.ch_id_dst = self.ch_id_src + self.ch_delta_id
        # str with the id pair
        self.ch_id_pair_str = f"{self.ch_id_src}_{self.ch_id_dst}"

    def validate_chapter_id(self) -> None:
        """Validate the chapter ids.

        s 0[xxxx] -> first=0
        d 0[xxxx] -> delta=0

        s 0[xxxx]    -> first=0
        d 1[...xxxx] -> delta=3

        s 0[xxxx]    -> first=0
        d 2[xxxx...]

        s 1[...xxxx] -> first=3
        d 0[xxxx]    -> delta=-3

        s 1[...xxxx] -> first=3
        d 1[...xxxx] -> delta=0

        s 1[...xxxx] -> first=3
        d 2[xxxx...] -> delta=-3

        s 2[xxxx...] -> ??? set max number of valid chapter?
        d 0[xxxx]    -> delta=0

        s 2[xxxx...]
        d 1[...xxxx] -> delta=3

        s 2[xxxx...]
        d 2[xxxx...] -> delta=0

        s 3[...xxxx...]
        d 3[...xxxx...] -> delta=0

        As we only update one of curr/first/delta,
        it makes sense to keep the validation in the funcs that change those values.

        The user must not be a fool.
        """

    def change_chapter_curr(self, direction: str) -> None:
        """Go and fix the next chapter."""
        # update the ch_curr_id
        if direction == "back":
            self.ch_curr_id -= 1
        elif direction == "forward":
            self.ch_curr_id += 1

        # validate the ch id

        # can never be negative
        if self.ch_curr_id < 0:
            self.ch_curr_id = 0

        # the number of chapters in the list for the two books
        num_ch_src = self.epubs["src"].chap_num
        num_ch_dst = self.epubs["dst"].chap_num

        # the possible new ids for src and dst
        ch_id_src_new = self.ch_curr_id + self.ch_first_id
        ch_id_dst_new = ch_id_src_new + self.ch_delta_id

        # we only ever increase by one, if any one fails we have a problem
        if ch_id_src_new > num_ch_src or ch_id_dst_new > num_ch_dst:
            self.ch_curr_id -= 1

        # TODO if we had a reliable chap_valid_num we could just check curr_id>valid_num
        # first should actually be an attribute of the epubs

        # update the other chap ids
        self.update_chapter_id_info()
        # compute the alignment for this pair
        self.align_auto()

    def change_chapter_delta(self, direction: str) -> None:
        """Change the delta between chapters. Also set which is the first."""
        # update the ch_delta
        if direction == "back":
            self.ch_delta_id -= 1
        elif direction == "forward":
            self.ch_delta_id += 1

        # TODO validation lol

        # update the other chap ids
        self.update_chapter_id_info()
        # compute the alignment for this pair
        self.align_auto()

    def select_src_sent(self) -> None:
        """Select a new src sent to align."""

    def pick_dst_par(self, id_dst_correct: int) -> None:
        """Pick which dst par is the right one for the currently selected src."""
        self.aligners[self.ch_id_pair_str].pick_dst_par(id_dst_correct)

    def scroll_sent(self, which_sents, direction) -> None:
        """Scroll the right bunch of sentences in the right direction."""

    def save_epub(self) -> None:
        """Build the interleaved epub."""
        # build the interleaved chaps
        # TODO this should be an attribute of the book
        ch_tot_num = len(self.epubs["src"].chapters)
        ep_tmpl_fol = get_package_fol("epub_template")

        # TODO se this via form in the /load route
        title_src = self.epubs["src"].epub_name
        title_dst = self.epubs["dst"].epub_name
        author = self.epubs["src"].epub_author
        book_title = f"{title_src} ({title_dst})"
        book_author = f"{author}"
        lt_pair_h = self.lts_ph[0]
        lang_alpha2_tag_src = self.sd_to_lt["src"]
        lang_alpha2_tag_dst = self.sd_to_lt["dst"]

        for ch_build_id in range(ch_tot_num):

            # the current chapters to align
            ch_id_src = self.ch_first_id + ch_build_id
            ch_src = self.epubs["src"].chapters[ch_id_src]
            ch_id_dst = ch_id_src + self.ch_delta_id
            ch_dst = self.epubs["dst"].chapters[ch_id_dst]

            # the matching file
            ch_id_pair_str = f"{ch_id_src}_{ch_id_dst}"
            align_info_name = f"info_align_{ch_id_pair_str}.json"
            par_matching_path = self.align_cache_fol / align_info_name

            interleave_chap(
                ch_src=ch_src,
                ch_dst=ch_dst,
                ch_viz_id=ch_build_id + 1,
                par_matching_path=par_matching_path,
                output_fol=self.output_fol,
                ep_tmpl_fol=ep_tmpl_fol,
                book_title=book_title,
                book_author=book_author,
                lt_pair_h=lt_pair_h,
                lang_alpha2_tag_src=lang_alpha2_tag_src,
                lang_alpha2_tag_dst=lang_alpha2_tag_dst,
            )

        # build the ep
        # MAYBE here we pass the src language tag
        eb = EpubBuilder(
            composed_folder=self.output_fol,
            template_epub_folder=ep_tmpl_fol,
            epub_out_folder=self.output_fol,
            tot_chapter_num=ch_tot_num,
            author_name_full=book_author,
            book_name_full=book_title,
            lang_alpha2_tag=lang_alpha2_tag_src,
        )
        eb.do_build()
