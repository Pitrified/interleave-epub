"""Initialize app package."""

from typing import Any

from flask import Flask

app = Flask(__name__)

# https://github.com/lepture/python-livereload/issues/144#issuecomment-256277989
app.config["TEMPLATES_AUTO_RELOAD"] = True

from interleave_epub.interleave.interactive import InterleaverInteractive

ii = InterleaverInteractive()

from interleave_epub.flask_app import routes
