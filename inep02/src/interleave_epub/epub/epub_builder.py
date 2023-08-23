"""Class to build an epub."""

from pathlib import Path
from shutil import copyfile, make_archive, rmtree


class EpubBuilder:
    """Build an epub from a collection of chapters."""

    def __init__(
        self,
        composed_folder: Path,
        template_epub_folder: Path,
        epub_out_folder: Path,
        tot_chapter_num: int,
        author_name_full: str,
        book_name_full: str,
        lang_alpha2_tag: str,
    ) -> None:
        """Initialize the epub builder.

        TODO: need to add

        .. css

            .lang-en {
                font-style: italic;
            }

        at the end of ``stylesheet.css``.

        Args:
            composed_folder (Path): Folder with the chapter xhtml files.
            template_epub_folder (Path): Folder with the epub template files.
            epub_out_folder (Path): Folder to use as output location.
            tot_chapter_num (int): Total number of chapters.
            author_name_full (str): Author name.
            book_name_full (str): Book name.
            lang_alpha2_tag (str): _description_
        """
        self._composed_folder = composed_folder
        self._tmpl_folder = template_epub_folder
        self.epub_out_folder = epub_out_folder
        self.tot_chapter_num = tot_chapter_num
        self.author_name_full = author_name_full
        self.book_name_full = book_name_full
        self.lang_alpha2_tag = lang_alpha2_tag

    def do_build(self) -> None:
        """Build the EPub.

        1. load the templates
        1. fill the dynamic files
        1. copy the static files
        1. make the zip and the epub
        """
        self._clean_title()

        # the base folder for the epub to work in
        if not self.epub_out_folder.exists():  # pragma: nocover
            self.epub_out_folder.mkdir(parents=True, exist_ok=True)

        # the folder that holds all the files that will be packed in the zip
        self._epub_files_folder = self.epub_out_folder / "epub_data"
        # if there is an old one remove it, or some previous files could be zipped
        if self._epub_files_folder.exists():  # pragma: nocover
            rmtree(self._epub_files_folder)
        # create the fresh one
        self._epub_files_folder.mkdir(parents=True, exist_ok=True)

        self._load_templates()

        self._build_dynamic()

        self._copy_static()

        self._create_epub_file()

    def _clean_title(self) -> None:
        """Create a name to use for the file, starting from the book title."""
        # TODO use werkzeug to clean the file name

        # substitute spaces with underscores
        clean_title = self.book_name_full.replace(" ", "_")

        # remove all non-printable characters
        printable = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
        clean_title = "".join(filter(lambda x: x in printable, clean_title))
        # logg.info(f"clean_title: {clean_title}")

        # if every character was non printable, invent a name
        if len(clean_title) == 0:  # pragma: nocover
            clean_title = "output_book"

        self.clean_title = clean_title

    def _load_templates(self) -> None:
        """Load the templates to be filled.

        - tmpl_content.opf
        - tmpl_preface.xhtml
        - tmpl_toc.ncx
        - tmpl_toc_navpoint.ncx
        Define small chunks to fill the manifest/spine in content.opf
        - tmpl_content_man
        - tmpl_content_spine
        """
        # logg.debug("Start _load_templates")

        # content.opf
        content_path = self._tmpl_folder / "tmpl_content.opf"
        self._tmpl_content = content_path.read_text()
        # logg.debug(f">>>>>> self._tmpl_content:\n{self._tmpl_content}")

        # manifest chunk template
        self._tmpl_content_man = '        <item href="{split_name}" id="{idref}" media-type="application/xhtml+xml" />\n'
        # logg.debug(f">>>>>> self._tmpl_content_man:\n{self._tmpl_content_man}")

        # spine chunk template
        self._tmpl_content_spine = '        <itemref idref="{idref}" />\n'
        # logg.debug(f">>>>>> self._tmpl_content_spine:\n{self._tmpl_content_spine}")

        # preface.xhtml
        preface_path = self._tmpl_folder / "tmpl_preface.xhtml"
        self._tmpl_preface = preface_path.read_text()
        # logg.debug(f">>>>>> self._tmpl_preface:\n{self._tmpl_preface}")

        # toc.ncx
        toc_path = self._tmpl_folder / "tmpl_toc.ncx"
        self._tmpl_toc = toc_path.read_text()
        # logg.debug(f">>>>>> self._tmpl_toc:\n{self._tmpl_toc}")

        # toc_navpoints template
        toc_nav_path = self._tmpl_folder / "tmpl_toc_navpoint.ncx"
        self._tmpl_toc_nav = toc_nav_path.read_text()
        # logg.debug(f">>>>>> self._tmpl_toc_nav:\n{self._tmpl_toc_nav}")

    def _build_dynamic(self) -> None:
        r"""Fill the templates to assemble the book.

        Keys to fill
        - preface.xhtml:
            * title
            * author
        - tmpl_content.opf:
            * author_file_as
            * author
            * title
            * all_manifest
            * all_spine
            * lang_alpha2_tag
        - self._tmpl_content_man:
            * split_name
            * idref
        - self._tmpl_content_spine:
            * idref
        - tmpl_toc.ncx:
            * title
            * all_navpoints
        - tmpl_toc_navpoint.ncx:
            * navpoint_id
            * play_order
            * chapter_title
            * path_src
        """
        # build these while going over the preface/chapters
        all_navpoints = ""
        all_manifest = ""
        all_spine = ""

        ###############################################################
        #    preface
        ###############################################################

        # add the preface to the navpoints (in toc.ncx)
        preface_name = "preface.xhtml"
        preface_navpoint_id = "chapter0"
        chunk_nav = self._tmpl_toc_nav.format(
            navpoint_id=preface_navpoint_id,
            play_order=0,
            chapter_title="Preface",
            path_src=preface_name,
        )
        all_navpoints += chunk_nav

        # add the preface to manifest and spine (in content.opf)
        preface_id_ref = "html0"
        chunk_man = self._tmpl_content_man.format(
            split_name=preface_name, idref=preface_id_ref
        )
        all_manifest += chunk_man
        chunk_spine = self._tmpl_content_spine.format(idref=preface_id_ref)
        all_spine += chunk_spine

        # build the preface by filling the template
        preface_filled = self._tmpl_preface.format(
            title=self.book_name_full, author=self.author_name_full
        )
        preface_path = self._epub_files_folder / preface_name
        preface_path.write_text(preface_filled)

        ###############################################################
        # add every chapter to navpoints/manifest/spine
        ###############################################################

        for chapter_index in range(1, self.tot_chapter_num + 1):

            # the name of the composed chapter
            composed_chapter_name = f"ch_{chapter_index:04d}.xhtml"
            # the location of the composed chapter
            composed_chapter_path = self._composed_folder / composed_chapter_name
            # the location of the chapter for the ebook
            epub_chapter_path = self._epub_files_folder / composed_chapter_name
            # copy the chapter
            copyfile(composed_chapter_path, epub_chapter_path)

            # the title of the chapter (for the navpoint)
            chapter_title = f"Chapter {chapter_index}"

            # add the chapter to the navpoints (in toc.ncx)
            chapter_nav_id = f"chapter{chapter_index}"
            chunk_nav = self._tmpl_toc_nav.format(
                navpoint_id=chapter_nav_id,
                play_order=chapter_index,
                chapter_title=chapter_title,
                path_src=composed_chapter_name,
            )
            all_navpoints += chunk_nav

            # add the chapter to manifest and spine (in content.opf)
            ch_id_ref = f"html{chapter_index}"
            chunk_man = self._tmpl_content_man.format(
                split_name=composed_chapter_name, idref=ch_id_ref
            )
            all_manifest += chunk_man
            chunk_spine = self._tmpl_content_spine.format(idref=ch_id_ref)
            all_spine += chunk_spine

        # logg.debug(f"all_navpoints:\n{all_navpoints}")
        # logg.debug(f"all_spine:\n{all_spine}")
        # logg.debug(f"all_manifest:\n{all_manifest}")

        ###############################################################
        # build content.opf
        ###############################################################

        content_filled = self._tmpl_content.format(
            author_file_as=self.author_name_full,
            author=self.author_name_full,
            title=self.book_name_full,
            all_manifest=all_manifest,
            all_spine=all_spine,
            lang_alpha2_tag=self.lang_alpha2_tag,
        )
        content_path = self._epub_files_folder / "content.opf"
        content_path.write_text(content_filled)

        ###############################################################
        # build the toc.ncx
        ###############################################################

        toc_filled = self._tmpl_toc.format(
            title=self.book_name_full, all_navpoints=all_navpoints
        )
        toc_path = self._epub_files_folder / "toc.ncx"
        toc_path.write_text(toc_filled)

    def _copy_static(self) -> None:
        r"""Copy the static files of the EPub."""
        meta_inf_folder = self._epub_files_folder / "META-INF"
        if not meta_inf_folder.exists():  # pragma: nocover
            meta_inf_folder.mkdir(parents=True, exist_ok=True)

        for file_name in [
            "META-INF/container.xml",
            "mimetype",
            "page_styles.css",
            "stylesheet.css",
        ]:
            orig_file_path = self._tmpl_folder / file_name
            new_file_path = self._epub_files_folder / file_name
            copyfile(orig_file_path, new_file_path)

    def _create_epub_file(self) -> None:
        r"""Compress the generated files and assemble the EPub."""
        # the epub final name
        epub_file_name = self.clean_title + ".epub"
        self.epub_file_path = self.epub_out_folder / epub_file_name
        if self.epub_file_path.exists():  # pragma: nocover
            self.epub_file_path.unlink()
        # logg.info(f"self.epub_file_path: {self.epub_file_path}")

        # the zip archive name
        zip_file_name = self.clean_title + ".zip"
        self.zip_file_path = self.epub_out_folder / zip_file_name
        # logg.debug(f"self.zip_file_path: {self.zip_file_path}")

        # the zip base name must be a string
        # and without the extension
        zip_file_base_name = self.clean_title
        self.zip_file_base_path = self.epub_out_folder / zip_file_base_name
        # logg.debug(f"self.zip_file_base_path: {self.zip_file_base_path}")
        base_name_zip = str(self.zip_file_base_path)

        # create the archive
        make_archive(
            base_name=base_name_zip,
            format="zip",
            root_dir=self._epub_files_folder,
            # dry_run=True,
            # logger=logg,
        )

        # rename it to epub
        self.zip_file_path.rename(self.epub_file_path)
