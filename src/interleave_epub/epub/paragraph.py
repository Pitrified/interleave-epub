"""Paragraph class."""

from bs4 import Tag
from spacy.language import Language
from spacy.tokens import Doc

from interleave_epub.epub import chapter
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class Paragraph:
    """Paragraph class.

    Split the paragraph in sentences using spacy and translate them using huggingface.
    """

    def __init__(
        self,
        p_tag: Tag,
        chapter: "chapter.Chapter",
    ) -> None:
        """Initialize a paragraph.

        TODO:
            Filter sentences that are too short?
                Do not split in sentences if the par is short.
                Merge short sentences.
        """
        # save a reference to the chapter containing this paragraph
        self.chapter = chapter

        # save various nlp tools
        self.nlp: dict[str, Language] = self.chapter.nlp
        self.pipe: dict[str, TranslationPipelineCache] = self.chapter.pipe
        self.lang_orig: str = self.chapter.lang_orig
        self.lang_dest: str = self.chapter.lang_dest
        self.lang_tr = f"{self.lang_orig}-{self.lang_dest}"

        # save the tag
        self.p_tag = p_tag

        # add lang info in the tag
        self.p_tag["lang_orig"] = self.lang_orig
        self.p_tag["class"] = self.p_tag.get("class", []) + [f"lang_{self.lang_orig}"]  # type: ignore
        # Operator "+" not supported for types "str | list[str] | None" and "list[str]"

        # MAYBE: move to method that does clean up well
        self.par_str = str(self.p_tag.string)  # we want a str, not a NavigableString
        self.par_str = self.par_str.replace("\n\r", " ")
        self.par_str = self.par_str.replace("\n", " ")
        self.par_str = self.par_str.replace("\r", " ")

        # TODO: improve sentence split
        self.par_doc = self.nlp[self.lang_orig](self.par_str)
        self.sents_orig = list(self.par_doc.sents)

        self.sents_tran: list[Doc] = []
        for sent in self.sents_orig:
            str_tran = self.pipe[self.lang_tr](sent.text)
            # sent_tran = self.nlp[self.lang_dest](str_tran[0]["translation_text"])
            sent_tran = self.nlp[self.lang_dest](str_tran)
            self.sents_tran.append(sent_tran)
