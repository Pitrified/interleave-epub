"""Paragraph class."""

from bs4 import Tag
from loguru import logger as lg
from spacy.language import Language
from spacy.tokens import Doc, Span

from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class Paragraph:
    """Paragraph class."""

    def __init__(
        self,
        p_tag: Tag,
        lang: dict[str, str],
        nlp: dict[str, Language],
        pipe: dict[str, TranslationPipelineCache],
    ) -> None:
        """Initialize a paragraph."""
        # save the tag
        self.p_tag = p_tag

        # save misc lang info
        self.lang = lang
        self.nlp = nlp
        self.pipe = pipe

        # MAYBE: move to method that does clean up well
        # TODO: can you use Tag.text ?
        # ptag_str = self.p_tag.string
        ptag_str = self.p_tag.text
        # lg.debug(f"ptag_str: ({type(ptag_str)}) >{ptag_str}<")
        if ptag_str is None:
            self.par_str = ""
        else:
            self.par_str = str(ptag_str)  # we want a str, not a NavigableString
            # TODO is Tag.text already a string?
            self.par_str = self.par_str.replace("\n\r", " ")
            self.par_str = self.par_str.replace("\n", " ")
            self.par_str = self.par_str.replace("\r", " ")

        # lg.debug(f"paragraph: >{self.par_str}<")
        # decide if the paragraph is empty
        min_par_len = 0
        if len(self.par_str) <= min_par_len:
            self.is_empty = True
            # an empty paragraph cannot be translated
            return
        self.is_empty = False

        # TODO: improve sentence split
        self.par_doc = self.nlp[self.lang["orig"]](self.par_str)
        self.sents: dict[str, list[Doc | Span]] = {}
        self.sents["orig"] = list(self.par_doc.sents)

        # translate the sentences
        self.sents["trad"] = []
        for sent in self.sents["orig"]:
            str_tran = self.pipe[self.lang["ot_pair_h"]](sent.text)
            sent_tran = self.nlp[self.lang["trad"]](str_tran)
            self.sents["trad"].append(sent_tran)

    def __repr__(self) -> str:
        """Repr of the paragraph."""
        s = f"num sents: {len(self.sents['trad'])}"
        for so, st in zip(self.sents["orig"], self.sents["trad"]):
            s += f"\n{so}"
            s += f"\n{st}"
        return s

    def get_text(self) -> str:
        """Get the text content of the paragraph."""
        return self.par_str
