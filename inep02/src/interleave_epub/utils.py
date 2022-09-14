"""Utility functions for the whole package."""


from pathlib import Path
from typing import Literal

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
