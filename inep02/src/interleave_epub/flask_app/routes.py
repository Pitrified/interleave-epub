"""Routes for the flask app."""

from flask import render_template, request

from interleave_epub.flask_app import app
from interleave_epub.flask_app.utils import flatten_multidict
from interleave_epub.interleave.constants import (
    lt_dst_default,
    lt_options,
    lt_src_default,
)


@app.route("/")
@app.route("/index")
def index():
    """Render the index page."""
    return render_template("index.html", title="Home")


@app.route("/learn01", methods=["GET", "POST"])
def learn01():
    """Render the learn 01 page, to learn the first thing."""
    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        print(f"{request.form=}")
        print(f"{request.files=}")

    lts_list = [
        {"tag": "en", "name": "English"},
        {"tag": "fr", "name": "French"},
    ]
    lt_src_default = "fr"
    lt_dst_default = "en"

    return render_template(
        "learn_html_01.html",
        title="Home",
        lts_list=lts_list,
        lt_src_default=lt_src_default,
        lt_dst_default=lt_dst_default,
    )


@app.route("/load", methods=["GET", "POST"])
def load_ep():
    """Render the page to pick the languages and load the epubs."""
    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        form_data = flatten_multidict(request.form)
        print(f"{form_data=}")
        files_data = flatten_multidict(request.files)
        print(f"{files_data=}")

        # parse the data
        # if everything is ok, go to /align
        # return redirect(url_for("epub_load"))

    return render_template(
        "load.html",
        lts_list=lt_options,
        lt_src_default=lt_src_default,
        lt_dst_default=lt_dst_default,
    )
