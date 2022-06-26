"""Chapter class."""
from typing import Literal

from bs4 import BeautifulSoup
from spacy.language import Language
from spacy.tokens import Span, Doc

from interleave_epub.epub import epub
from interleave_epub.epub.paragraph import Paragraph
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class Chapter:
    """Chapter class.

    Parse the chapter content to find the Paragraphs in <p> tags.
    """

    def __init__(
        self,
        chap_content: bytes,
        chap_file_name: str,
        epub: "epub.EPub",
    ) -> None:
        """Initialize a chapter.

        TODO:
            Pass lang tags?
        """
        self.chap_file_name = chap_file_name
        self.epub = epub

        self.nlp: dict[str, Language] = self.epub.nlp
        self.pipe: dict[str, TranslationPipelineCache] = self.epub.pipe
        self.lang_orig: str = self.epub.lang_orig
        self.lang_dest: str = self.epub.lang_dest

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
        for p_tag in self.all_p_tag[:]:
            self.paragraphs.append(Paragraph(p_tag, self))

        self.build_index()
        self.build_flat_sents()

    def build_index(self):
        """Build maps to go from ``sent_in_chap_id`` to ``(par_id, sent_in_par_id)`` and vice-versa."""
        self.parsent_to_sent = {}
        self.sent_to_parsent = {}
        sc_id = 0
        for p_id, par in enumerate(self.paragraphs):
            for sp_id, sent in enumerate(par.sents_orig):
                self.parsent_to_sent[(p_id, sp_id)] = sc_id
                self.sent_to_parsent[sc_id] = (p_id, sp_id)
                sc_id += 1

    def build_flat_sents(self):
        """Build lists of sentences in the chapter, as Doc and text."""
        # original sentences
        self.sents_text_orig = []
        self.sents_doc_orig = []
        for _, sent_orig in self.enumerate_sents(which_sent="orig"):
            self.sents_text_orig.append(sent_orig.text)
            self.sents_doc_orig.append(sent_orig)

        # translated sentences
        self.sents_text_tran = []
        self.sents_doc_tran = []
        for _, sent_tran in self.enumerate_sents(which_sent="tran"):
            self.sents_text_tran.append(sent_tran.text)
            self.sents_doc_tran.append(sent_tran)

        # the number of sentences in this chapter
        self.sents_num = len(self.sents_text_orig)

    def enumerate_sents(self, start_par: int = 0, end_par: int = 0, which_sent="orig"):
        """Enumerate all the sentences in the chapter, indexed as (par_id, sent_id)."""
        if end_par == 0:
            end_par = len(self.paragraphs) + 1
        for i_p, par in enumerate(self.paragraphs[start_par:end_par]):
            for i_s, sent in enumerate(par.sents_orig):
                if which_sent == "orig":
                    yield (i_p + start_par, i_s), sent
                elif which_sent == "tran":
                    yield (i_p + start_par, i_s), par.sents_tran[i_s]

    def get_sent_with_parsent_id(
        self, par_id: int, sent_id: int, which_sent=Literal["orig", "tran"]
    ) -> Doc | Span:
        """Get the sentence in the chapter indexed as (par_id, sent_id)."""
        if which_sent == "orig":
            return self.paragraphs[par_id].sents_orig[sent_id]
        else:
            return self.paragraphs[par_id].sents_tran[sent_id]

    def get_sent_with_chapsent_id(
        self, chapsent_id: int, which_sent=Literal["orig", "tran"]
    ) -> Doc | Span:
        """Get the sentence in the chapter indexed as the sentence number in the chapter."""
        par_id, sent_id = self.sent_to_parsent[chapsent_id]
        if which_sent == "orig":
            return self.paragraphs[par_id].sents_orig[sent_id]
        else:
            return self.paragraphs[par_id].sents_tran[sent_id]
