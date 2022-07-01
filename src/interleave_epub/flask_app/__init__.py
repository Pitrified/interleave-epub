"""Initialize app package."""
from typing import Any

from flask import Flask

app = Flask(__name__)

# global state
gs: dict[str, Any] = {}

from interleave_epub.flask_app import routes
