"""Chapter class."""
from typing import Literal

from bs4 import BeautifulSoup

from interleave_epub.epub import epub
from interleave_epub.epub.paragraph import Paragraph


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
        """Initialize a chapter."""
        # save and extract misc info
        self.chap_file_name = chap_file_name
        self.epub = epub
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
