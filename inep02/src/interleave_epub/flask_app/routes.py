"""Routes for the flask app."""

from flask import render_template

from interleave_epub.flask_app import app


@app.route("/")
@app.route("/index")
def index():
    """Render the index page."""
    return render_template("index.html", title="Home")
