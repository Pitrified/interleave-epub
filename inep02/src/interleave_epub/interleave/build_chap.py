"""Build an interleaved chapter given a paragraph matching."""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from loguru import logger as lg

from interleave_epub.epub.chapter import Chapter


def interleave_chap(
    ch_src: Chapter,
    ch_dst: Chapter,
    ch_viz_id: int,
    par_matching_path: Path,
    output_fol: Path,
    ep_tmpl_fol: Path,
    book_title: str,
    book_author: str,
    lt_pair_h: str,
):
    """Build an interleaved chapter given a paragraph matching.

    Fill 5 keys in tmpl_ch:
    * book_title
    * book_author
    * composed_tag
    * chapter_title
    * chapter_content

        0 1 2 3
        1 1 1 2 -> repeated dst ids

        0 1 2 3
        0 2 4 5 -> missing dst ids

    par_dst_id is the chapter id *up to* which you can add,
    that par must be shown after
    """
    # load the matching
    align_info = json.loads(par_matching_path.read_text())
    tmp: dict[int, int] = align_info["better_par_src_to_dst_flat"]
    # json files treat keys as string
    par_src_to_dst_flat = {int(k): v for k, v in tmp.items()}

    last_dst_par_id = -1
    composed_ch_htext = ""

    # add the chapters using the matching
    for par_src_id, par_dst_id in par_src_to_dst_flat.items():
        if par_dst_id > last_dst_par_id:
            for new_dst_par_id in range(last_dst_par_id + 1, par_dst_id):
                # lg.debug(f"add     dst par {new_dst_par_id}")
                composed_ch_htext += f"{ch_dst.paragraphs[new_dst_par_id].p_tag}\n"
                last_dst_par_id = new_dst_par_id
        # lg.debug(f"add src     par {par_src_id}")
        composed_ch_htext += f"{ch_src.paragraphs[par_src_id].p_tag}\n"

    # add all the still missing dst par
    dst_par_num = len(ch_dst.paragraphs)
    for new_dst_par_id in range(last_dst_par_id + 1, dst_par_num):
        # lg.debug(f"add     dst par {new_dst_par_id}")
        composed_ch_htext += f"{ch_dst.paragraphs[new_dst_par_id].p_tag}\n"

    # build a vague chapter title
    chapter_title = f"Chapter {ch_viz_id}"

    # load the chapter template
    tmpl_ch_path = ep_tmpl_fol / "tmpl_ch.xhtml"
    tmpl_ch = tmpl_ch_path.read_text()

    # fill the template
    full_ch_text = tmpl_ch.format(
        book_title=book_title,
        book_author=book_author,
        composed_tag=lt_pair_h,
        chapter_title=chapter_title,
        chapter_content=composed_ch_htext,
    )

    # where to save the chapter
    composed_ch_path = output_fol / f"ch_{ch_viz_id:04d}.xhtml"
    lg.debug(f"Saving in {composed_ch_path}")

    # build a soup for the chapter content
    parsed_text = BeautifulSoup(full_ch_text, features="html.parser")
    # write the prettified text
    composed_ch_path.write_text(parsed_text.prettify())
