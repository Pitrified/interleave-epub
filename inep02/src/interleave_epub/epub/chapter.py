"""Chapter class."""
from typing import Literal, get_args

from bs4 import BeautifulSoup
from spacy.language import Language

from interleave_epub.epub.paragraph import Paragraph
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache
from interleave_epub.utils import orig_or_trad


class Chapter:
    """Chapter class.

    Parse the chapter content to find the Paragraphs in <p> tags.
    """

    def __init__(
        self,
        chap_content: bytes,
        chap_file_name: str,
        lang: dict[str, str],
        nlp: dict[str, Language],
        pipe: dict[str, TranslationPipelineCache],
    ) -> None:
        """Initialize a chapter."""
        # save and extract misc info
        self.chap_file_name = chap_file_name
        self.lang = lang
        self.nlp = nlp
        self.pipe = pipe

        # parse the soup and get the body
        self.soup = BeautifulSoup(chap_content, features="html.parser")
        self.body = self.soup.body
        if self.body is None:
            print(f"No body found in chapter {self.chap_file_name} of book {'book'}.")
            return

        # find the paragraphs
        self.all_p_tag = self.body.find_all("p")
        if len(self.all_p_tag) == 0:
            print(
                f"No paragraphs found in chapter {self.chap_file_name} of book {'book'}."
            )
            return

        # build the list of Paragraphs
        # self.paragraphs = [Paragraph(p_tag, self.nlp) for p_tag in self.all_p_tag]
        self.paragraphs: list[Paragraph] = []
        for p_tag in self.all_p_tag[:5]:
            self.paragraphs.append(
                Paragraph(
                    p_tag,
                    self.lang,
                    self.nlp,
                    self.pipe,
                )
            )

        self.build_flat_sents()

    def enumerate_sents(
        self, which_sent: orig_or_trad, start_par: int = 0, end_par: int = 0
    ):
        """Enumerate all the sentences in the chapter, indexed as (par_id, sent_id)."""
        if end_par == 0:
            end_par = len(self.paragraphs) + 1
        for i_p, par in enumerate(self.paragraphs[start_par:end_par]):
            for i_s, sent in enumerate(par.sents[which_sent]):
                yield (i_p + start_par, i_s), sent

    def build_flat_sents(self) -> None:
        """Build lists of sentences in the chapter, as Doc and text."""
        self.sents_text: dict[str, list[str]] = {}
        self.sents_doc: dict[str, list[str]] = {}
        self.sents_psid: dict[str, list[tuple[int, int]]] = {}
        self.sents_len: dict[str, list[int]] = {}
        self.sents_num: dict[str, int] = {}

        # https://github.com/python/mypy/issues/9230#issuecomment-789230275
        for which_sent in get_args(orig_or_trad):
            self.sents_text[which_sent] = []
            self.sents_doc[which_sent] = []
            self.sents_psid[which_sent] = []
            self.sents_len[which_sent] = []
            for sent_psid, sent in self.enumerate_sents(which_sent):
                self.sents_text[which_sent].append(sent.text)
                self.sents_doc[which_sent].append(sent)
                self.sents_psid[which_sent].append(sent_psid)
                self.sents_len[which_sent].append(len(sent))
            self.sents_num[which_sent] = len(self.sents_text[which_sent])
