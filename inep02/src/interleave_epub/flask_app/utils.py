"""Misc functions to support Flask apps."""

import base64
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


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


# def flatten_multidict(md: ImmutableMultiDict) -> dict:
def flatten_multidict(md) -> dict:
    """Flatten a multi dict, hoping that there are no key conflicts."""
    return {k: md[k] for k in md}


def permanentize_form_file(uploaded_file: FileStorage) -> tuple[str, io.BytesIO]:
    """Save to memory the content of the SpooledTemporaryFile."""
    file_name = uploaded_file.filename
    file_name = file_name if file_name is not None else ""
    file_name = secure_filename(file_name)

    if file_name == "":
        return file_name, io.BytesIO()

    # uploaded_file.stream is a SpooledTemporaryFile:
    # read the contents as bytes and permanentize them
    file_bytes_content = uploaded_file.stream.read()
    # convert the bytes back to a stream, now linked to permanent data
    file_io_stream = io.BytesIO(file_bytes_content)

    return file_name, file_io_stream
