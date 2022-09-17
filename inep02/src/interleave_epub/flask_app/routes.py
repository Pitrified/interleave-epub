"""Routes for the flask app."""

from pathlib import Path

from flask import redirect, render_template, request, url_for
from loguru import logger as lg

from interleave_epub.flask_app import app, ii
from interleave_epub.flask_app.render import render_align, render_load
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
    print(f"{request=}")
    if request.method == "POST":
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
            # we cheat for maximum laziness
            epub_folder_path = Path("~").expanduser() / "snippet" / "datasets" / "ebook"
            epub_paths = {
                "fr": epub_folder_path
                / "Gaston_Leroux_-_Le_Mystere_de_la_chambre_jaune.epub",
                "en": epub_folder_path / "mystery_yellow_room.epub",
            }
            file_name_src = "ChambreJaune"
            file_name_dst = "YellowRoom"
            file_io_src = epub_paths["fr"]
            file_io_dst = epub_paths["en"]
            # return render_load()

        # set the lang tags
        ii.set_lang_tag(lt_src, "src")
        ii.set_lang_tag(lt_dst, "dst")

        # load the models
        ii.load_nlp()

        # load the books
        ii.add_book(file_io_src, "src", file_name_src)
        ii.add_book(file_io_dst, "dst", file_name_dst)

        # go forth and align
        return redirect(url_for("align", first_align=""))

    return render_load()


@app.route("/align", methods=["GET", "POST"])
def align():
    """Align two epubs."""
    # parse POST request
    print(f"{request=}")
    if request.method == "POST":
        form_data = flatten_multidict(request.form)
        print(f"{form_data=}")
        files_data = flatten_multidict(request.files)
        print(f"{files_data=}")

    # parse GET request
    elif request.method == "GET":
        args_data = flatten_multidict(request.args)
        print(f"{args_data=}")

        if "first_align" in args_data:
            ii.align_auto()
        elif "dst_pick" in args_data:
            dst_pick = int(args_data["dst_pick"])
            ii.pick_dst_sent(dst_pick)

    return render_align(ii)
