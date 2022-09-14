"""Initialize app package."""
from typing import Any

from flask import Flask
from werkzeug.routing import IntegerConverter

app = Flask(__name__)

from interleave_epub.flask_app import routes
