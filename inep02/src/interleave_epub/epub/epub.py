"""EPub class."""

from collections import Counter
from pathlib import Path
import re
from typing import IO, Union
import zipfile

from spacy.language import Language
from tqdm import tqdm

from interleave_epub.epub.chapter import Chapter
from interleave_epub.epub.utils import VALID_CHAP_EXT
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache


class EPub:
    """EPub class."""

    def __init__(
        self,
        zipped_file: Union[str, IO[bytes], Path],
        epub_name: str,
        lang_orig: str,
        lang_trad: str,
        nlp: dict[str, Language],
        pipe: dict[str, TranslationPipelineCache],
    ) -> None:
        """Initialize an epub."""
        # load the file in memory
        self.zipped_file = zipped_file
        self.input_zip = zipfile.ZipFile(self.zipped_file)

        # save misc info
        self.epub_name = epub_name
        self.lang = {
            "orig": lang_orig,
            "trad": lang_trad,
            "ot_pair_h": f"{lang_orig}-{lang_trad}",  # orig trad pair hyphen
            "ot_pair_u": f"{lang_orig}_{lang_trad}",  # orig trad pair underscore
        }
        self.nlp = nlp
        self.pipe = pipe

        # analyze the contents and find the chapter file names
        self.zipped_file_paths = [Path(p) for p in self.input_zip.namelist()]
        self.find_text_chapters()

        # build a dict of chapters
        self.chapters: dict[int, Chapter] = {}
        for chap_id, chap_file_name in enumerate(tqdm(self.chap_file_names[:1])):
            self.chapters[chap_id] = Chapter(
                self.input_zip.read(chap_file_name),
                chap_file_name,
                self.lang,
                self.nlp,
                self.pipe,
            )

    def find_text_chapters(self) -> None:
        """Find and sort the chapter paths and names.
        
        Look for paths that match a regex ``name{number}`` and sort on ``number``.
        """
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
        self.chap_file_names = [str(p) for p in self.chap_file_paths]
