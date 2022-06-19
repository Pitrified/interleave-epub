"""Routes for the flask app."""
from flask import render_template
from interleave_epub.flask_app import app, gs
from interleave_epub.flask_app.asset_loader import pipe_loader


@app.route("/")
@app.route("/index")
def index():
    """Render the index page."""
    pipe_loader()
    print(gs)

    lt = "en"
    lt_other = "fr"
    pipe_key = f"pipe_{lt}_{lt_other}"
    tran = gs[pipe_key]("Does the pipeline work for translation tasks?")
    print(f"translation {tran}")
    return render_template("index.html", title="Home")
