"""Read the model state and render the html pages."""

from flask import render_template

from interleave_epub.interleave.constants import (
    lt_dst_default,
    lt_options,
    lt_src_default,
)


def render_load():
    """Render the load page."""
    return render_template(
        "load.html",
        lts_list=lt_options,
        lt_src_default=lt_src_default,
        lt_dst_default=lt_dst_default,
    )
