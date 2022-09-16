"""Routes for the flask app."""

from flask import redirect, render_template, request, url_for
from loguru import logger as lg

from interleave_epub.flask_app import app
from interleave_epub.flask_app.render import render_load
from interleave_epub.flask_app.utils import flatten_multidict, permanentize_form_file


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
        file_name_src, file_io_src = permanentize_form_file(files_data["file_src"])
        file_name_dst, file_io_dst = permanentize_form_file(files_data["file_dst"])
        lt_src = form_data["lt_src"]
        lt_dst = form_data["lt_dst"]

        # if some file is bad render the load page again
        if file_name_src == "" or file_name_dst == "":
            lg.warning(f"Empty filenames.")
            return render_load()

        # TODO: add the books to the Interleaver lol

        # go forth and align
        return redirect(url_for("align"))

    return render_load()


@app.route("/align", methods=["GET", "POST"])
def align():
    """Align two epubs."""
    return "Align."
