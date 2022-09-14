"""Misc functions to support Flask apps."""

import base64
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def fig2imgb64str(fig: Figure) -> str:
    """Encode a matplotlib figure as a base64 string.

    In the jinja2 template use the following <img> to add the plot::

        <img src="{{ image }}"/>
    """
    # convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvasAgg(fig).print_png(pngImage)

    # encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode("utf8")

    return pngImageB64String
