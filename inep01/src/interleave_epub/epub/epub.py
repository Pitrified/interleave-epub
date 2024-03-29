"""EPub class."""

from collections import Counter
from pathlib import Path
import re
from typing import IO, Union
import zipfile

from spacy.language import Language
from tqdm import tqdm

from interleave_epub.epub import chapter
from interleave_epub.epub.utils import VALID_CHAP_EXT
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class EPub:
    """EPub class."""

    def __init__(
        self,
        zipped_file: Union[str, IO[bytes], Path],
        nlp: dict[str, Language],
        pipe: dict[str, TranslationPipelineCache],
        lang_orig: str,
        lang_dest: str,
    ) -> None:
        """Initialize an epub.

        TODO:
            Pass file name? Yes, better debug. No can do with streamlit...
                But I'd rather pass a fake name inside streamlit,
                and the real one usually.
        """
        self.nlp = nlp
        self.pipe = pipe
        self.lang_orig = lang_orig
        self.lang_dest = lang_dest

        # load the file in memory
        self.zipped_file = zipped_file
        self.input_zip = zipfile.ZipFile(self.zipped_file)

        # analyze the contents and find the chapter file names
        self.zipped_file_paths = [Path(p) for p in self.input_zip.namelist()]
        self.get_text_chapters()
        self.chap_file_names = [str(p) for p in self.chap_file_paths]

        # build a list of chapters
        # self.chapters = [
        #     Chapter(self.input_zip.read(chap_file_name), chap_file_name, self.nlp)
        #     for chap_file_name in self.chap_file_names
        # ]
        self.chapters: list["chapter.Chapter"] = []
        # for chap_file_name in self.chap_file_names[:6]:
        for chap_file_name in tqdm(self.chap_file_names[:]) :
            self.chapters.append(
                chapter.Chapter(
                    self.input_zip.read(chap_file_name),
                    chap_file_name,
                    self,
                )
            )

    def get_text_chapters(self) -> None:
        """Find the chapters names that match a regex ``name{number}`` and sort on ``number``."""
        # get the paths that are valid xhtml and similar
        self.chap_file_paths = [
            f for f in self.zipped_file_paths if f.suffix in VALID_CHAP_EXT
        ]

        # stem gets the file name without extensions
        stems = [f.stem for f in self.chap_file_paths]

        # get the longest stem
        max_stem_len = max(len(c) for c in stems)

        # track the best regex' performances
        best_match_num = 0
        best_stem_re = re.compile("")

        # iterate over the len, looking for the best match
        for num_kept_chars in range(max_stem_len):

            # keep only the beginning of the names
            stem_chops = [s[:num_kept_chars] for s in stems]

            # count how many names have common prefix
            stem_freqs = Counter(stem_chops)

            # if there are no chapters with common prefix skip
            if stem_freqs.most_common()[0][1] == 1:
                continue

            # try to match the prefix with re
            for stem_might, stem_freq in stem_freqs.items():

                # compile a regex looking for name{number}
                stem_re = re.compile(f"{stem_might}(\\d+)")

                # how many matches this stem has
                good_match_num = 0

                # track if a regex fails: it can have some matches and then fail
                failed = False

                for stem in stems:
                    stem_ch = stem[:num_kept_chars]
                    match = stem_re.match(stem)

                    # if the regex does not match but the stem prefix does, fails
                    if match is None and stem_ch == stem_might:
                        failed = True
                        break

                    good_match_num += 1

                # if this stem failed to match, don't consider it for the best
                if failed:
                    continue

                # update info on best matching regex
                if good_match_num > best_match_num:
                    best_stem_re = stem_re
                    best_match_num = good_match_num

        # if the best match sucks keep all chapters
        if best_match_num <= 2:
            return

        # pair chapter name and chapter number
        chap_file_paths_id: list[tuple[Path, int]] = []
        for stem, chap_file_path in zip(stems, self.chap_file_paths):

            # match the stem and get the chapter number
            match = best_stem_re.match(stem)
            if match is None:
                continue
            chap_id = int(match.group(1))
            chap_file_paths_id.append((chap_file_path, chap_id))

        # sort the list according to the extracted id
        self.chap_file_paths = [
            cid[0] for cid in sorted(chap_file_paths_id, key=lambda x: x[1])
        ]

    def get_chapter_by_name(self, chap_file_name: str) -> "chapter.Chapter":
        """Get the chapter with the requested name."""
        chap_id = self.chap_file_names.index(chap_file_name)
        print(chap_id)
        return self.chapters[chap_id]
