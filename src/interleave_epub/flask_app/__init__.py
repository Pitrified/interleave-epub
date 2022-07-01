"""Initialize app package."""
from typing import Any

from flask import Flask
from werkzeug.routing import IntegerConverter

app = Flask(__name__)

# global state
gs: dict[str, Any] = {}


class SignedIntConverter(IntegerConverter):
    """Allow negative integers in the url.

    https://github.com/pallets/flask/issues/2643#issuecomment-368955087
    """

    regex = r"-?\d+"


app.url_map.converters["signed_int"] = SignedIntConverter

from interleave_epub.flask_app import routes
