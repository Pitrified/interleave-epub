"""Paragraph class."""

from bs4 import Tag
from spacy.language import Language
from spacy.tokens import Doc, Span

from interleave_epub.epub import chapter
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class Paragraph:
    """Paragraph class."""

    def __init__(
        self,
        p_tag: Tag,
        chapter: "chapter.Chapter",
    ) -> None:
        """Initialize a paragraph."""
        # save the tag
        self.p_tag = p_tag

        # save a reference to the chapter containing this paragraph
        self.chapter = chapter

        # save misc lang info
        # MAYBE: use dict self.lang_tag['orig'] ?
        # also everywhere else in the aligner src/dst are used, does it make sense to use them here ?
        self.lang_orig: str = self.chapter.lang_orig
        self.lang_dest: str = self.chapter.lang_dest
        self.lang_tr = f"{self.lang_orig}-{self.lang_dest}"

        # save various nlp tools
        self.nlp: dict[str, Language] = self.chapter.epub.nlp
        self.pipe: dict[str, TranslationPipelineCache] = self.chapter.epub.pipe

        # MAYBE: move to method that does clean up well
        # TODO: can you use Tag.text ?
        self.par_str = str(self.p_tag.string)  # we want a str, not a NavigableString
        self.par_str = self.par_str.replace("\n\r", " ")
        self.par_str = self.par_str.replace("\n", " ")
        self.par_str = self.par_str.replace("\r", " ")

        # TODO: improve sentence split
        self.par_doc = self.nlp[self.lang_orig](self.par_str)
        self.sents: dict[str, list[Doc | Span]] = {}
        self.sents["orig"] = list(self.par_doc.sents)

        # translate the sentences
        self.sents["trad"] = []
        for sent in self.sents["orig"]:
            str_tran = self.pipe[self.lang_tr](sent.text)
            sent_tran = self.nlp[self.lang_dest](str_tran)
            self.sents["trad"].append(sent_tran)
