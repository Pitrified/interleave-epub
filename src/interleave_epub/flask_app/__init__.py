"""Initialize app package."""
from flask import Flask

app = Flask(__name__)

# global state
gs = {}

from interleave_epub.flask_app import routes
