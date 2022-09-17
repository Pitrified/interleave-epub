"""Utility functions for the whole package."""


from pathlib import Path
from typing import Any, Literal

from loguru import logger as lg

src_or_dst = Literal["src", "dst"]
orig_or_trad = Literal["orig", "trad"]


def get_package_fol(
    which_fol: Literal[
        "root",
        "align_cache",
        "epub_template",
    ]
) -> Path:
    """Get the requested folder."""
    this_file_fol = Path(__file__).absolute().parent
    root_fol = this_file_fol.parent.parent

    if which_fol == "root":
        return root_fol
    elif which_fol == "align_cache":
        # this one might actually be put somewhere else
        # is not part of the package, but a temporary one for the user
        return root_fol / "align_cache"
    elif which_fol == "epub_template":
        return root_fol / "assets" / "epub_template"


def validate_index(
    index: int,
    list_: list[Any],
    allow_negative_index: bool = False,
) -> int:
    """Validate an index so that it is valid for a list."""
    len_list = len(list_)
    min_index = -len_list if allow_negative_index else 0
    if min_index <= index < len_list:
        return index
    if index >= len_list:
        return len_list - 1
    return min_index


def is_index_valid(
    index: int,
    list_: list[Any],
    allow_negative_index: bool = False,
) -> bool:
    """Return true if the index is valid."""
    valid_index = validate_index(index, list_, allow_negative_index)
    if valid_index == index:
        return True
    return False
