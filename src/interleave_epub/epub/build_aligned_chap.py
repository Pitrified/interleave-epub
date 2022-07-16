"""Given a bunch of sentence matching, pair up the paragraph.

Output a bunch of chapter files 
https://github.com/Pitrified/chapter-align/blob/main/src/chapter_align/build_epub.py#L216 ::

    composed_chapter_name = f"ch_{chapter_index:04d}.xhtml"


https://github.com/Pitrified/chapter-align/blob/main/src/chapter_align/align.py#L647 ::

    # get the template path
    template_epub_folder = get_package_folders("template_epub")
    tmpl_ch_path = template_epub_folder / "tmpl_ch.xhtml"
    # load the template
    tmpl_ch = tmpl_ch_path.read_text()

    ...

        # create the full chapter text
        full_ch_text = tmpl_ch.format(
            book_title=book_name_full,
            book_author=author_name_full,
            composed_tag=composed_tag,
            chapter_title=chapter_title,
            chapter_content=composed_chapter_text,
        )
"""

from itertools import groupby
import json
from operator import itemgetter
from pathlib import Path

from more_itertools import lstrip
from interleave_epub.epub.epub import EPub
from interleave_epub.flask_app import gs


def build_aligned_epub():
    """Build the aligned EPub.

    1. Merge the various chapters.
    1. Build the epub.
    """
    print(f"\n----- build epub -----")

    # # reload the sentences and some info on the ids
    # sents_info = gs["sents_info"]
    # sents_text_src_orig = sents_info["sents_text_src_orig"]
    # sents_psid_src_orig = sents_info["sents_psid_src_orig"]
    # sents_text_dst_orig = sents_info["sents_text_dst_orig"]
    # sents_psid_dst_orig = sents_info["sents_psid_dst_orig"]
    # sents_text_dst_tran = sents_info["sents_text_dst_tran"]
    # sents_psid_dst_tran = sents_info["sents_psid_dst_tran"]
    # sents_len_src_orig = sents_info["sents_len_src_orig"]
    # sents_len_dst_orig = sents_info["sents_len_dst_orig"]
    # sents_len_dst_tran = sents_info["sents_len_dst_tran"]

    # for mild sanity extract some values
    lts: dict[str, str] = gs["lts"]
    lt_src: str = gs["sd_to_lang"]["src"]
    lt_dst: str = gs["sd_to_lang"]["dst"]
    epub: dict[str, EPub] = gs["epub"]
    cache_fol: Path = gs["cache_fol"]

    # match info cache location
    chap_curr_delta = gs["chap_curr_delta"]
    match_info_path = cache_fol / f"match_info_{chap_curr_delta}.json"

    # build the chap id for each epub
    chap_id_start = {lt: 0 for lt in gs["lts"]}
    chap_id = {lt: chap_id_start[lt] + chap_curr_delta for lt in gs["lts"]}
    # get the actual chapter objects
    chap_curr = {lt: epub[lt].chapters[chap_id[lt]] for lt in lts}

    print(f"found match info at {match_info_path}")
    match_info = json.loads(match_info_path.read_text())
    all_i = match_info["all_i"]
    all_max_flattened = match_info["all_max_flattened"]

    print(
        f"{len(all_i)} {len(all_max_flattened)}"
        f" {len(chap_curr[lt_src].sents_psid)} {len(chap_curr[lt_dst].sents_psid)}"
    )

    # for j, (src_i, dst_i, src_psid, dst_psid) in enumerate(
    #     zip(all_i, all_max_flattened, sents_psid_src_orig, sents_psid_dst_orig)
    # ):
    #     print(f"{src_i} {src_psid} {dst_i} {dst_psid}")

    # pid of the next paragraph to write
    dst_p_to_write = 0
    src_p_to_write = 0

    all_max_psid = [chap_curr[lt_dst].sents_psid[dst_i] for dst_i in all_max_flattened]

    # the composed chapter
    composed_chapter_text = ""

    # group by dest paragraph number
    for k, v in groupby(
        zip(
            all_i,
            all_max_flattened,
            chap_curr[lt_src].sents_psid,
            # chap_curr[lt_dst].sents_psid,
            all_max_psid,
            # sents_psid_src_orig,
            # sents_psid_dst_orig,
        ),
        lambda x: x[3][0],
    ):
        v = list(v)
        print(f"---- {k}")
        for vel in v:
            print(vel)

        # the minimum src paragraph seen
        first_match_in_group = v[0]
        min_src_p = first_match_in_group[2][0]
        # we can print src paragraph before this one
        # and we print them before the dst paragraphs

        # the max dst paragraph seen
        # we can print dst paragraph before this one
        # there might be missing values in the k grouping, so we fill them like this
        # last_match_in_group = v[-1]
        # max_dst_p = last_match_in_group[3][0]
        max_dst_p = k

        print(f"{min_src_p=} {max_dst_p=}")

        # first we print all src that are before the current dst p
        for src_pid in range(src_p_to_write, min_src_p):
            composed_chapter_text += f"{chap_curr[lt_src].paragraphs[src_pid].p_tag}\n"
            print(f"src     {src_pid}")
            src_p_to_write = src_pid + 1
        # then we print all dst, that might be more than just k if the matching skipped a par
        for dst_pid in range(dst_p_to_write, max_dst_p + 1):
            composed_chapter_text += f"{chap_curr[lt_dst].paragraphs[dst_pid].p_tag}\n"
            print(f"    dst {dst_pid}")
            dst_p_to_write = dst_pid + 1

    print(f"---- finishing")
    # print the remaining dst paragraphs
    for dst_pid in range(dst_p_to_write, len(chap_curr[lt_dst].paragraphs) + 1):
        print(f"    dst {dst_pid}")
        dst_p_to_write = dst_pid + 1
    # print the remaining src paragraphs
    for src_pid in range(src_p_to_write, len(chap_curr[lt_src].paragraphs) + 1):
        print(f"src     {src_pid}")
        src_p_to_write = src_pid + 1

    print(f"----- build epub done -----\n")

    composed_path = cache_fol / f"composed_{chap_curr_delta}.txt"
    composed_path.write_text(composed_chapter_text)
