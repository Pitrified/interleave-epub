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
        lg.debug(f"{request=}")
        lg.debug(f"{request.form=}")
        lg.debug(f"{request.files=}")

    lts_list = [
        {"tag": "en", "name": "English"},
        {"tag": "fr", "name": "French"},
        {"tag": "br", "name": "Brazilian"},
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
    lg.debug(f"{request=}")
    if request.method == "POST":
        form_data = flatten_multidict(request.form)
        lg.debug(f"{form_data=}")
        files_data = flatten_multidict(request.files)
        lg.debug(f"{files_data=}")

        # parse the data
        file_name_src, file_io_src = permanentize_form_file(files_data["file_src"])
        file_name_dst, file_io_dst = permanentize_form_file(files_data["file_dst"])
        lt_src = form_data["lt_src"]
        lt_dst = form_data["lt_dst"]

        # TODO should be set more seriously
        file_author = ""

        # if some file is bad render the load page again
        if file_name_src == "" or file_name_dst == "":
            lg.warning(f"Empty filenames.")

            # we cheat for maximum laziness

            # gaston
            epub_folder_path = (
                Path("~").expanduser() / "repos" / "snippet" / "datasets" / "ebook"
            )
            epub_paths = {
                "fr": epub_folder_path
                / "Gaston_Leroux_-_Le_Mystere_de_la_chambre_jaune.epub",
                "en": epub_folder_path / "mystery_yellow_room.epub",
            }
            file_name_src = "ChambreJaune"
            file_name_dst = "YellowRoom"
            file_io_src = epub_paths["fr"]
            file_io_dst = epub_paths["en"]

            # paulo
            epub_folder_path = (
                Path("~").expanduser() / "ephem" / "calibrelibrary" / "Paulo Coelho"
            )
            # ~/ephem/calibrelibrary/Paulo Coelho/The Alchemist - edit - short (6)/The Alchemist - edit - short - Paulo Coelho.epub
            # ~/ephem/calibrelibrary/Paulo Coelho/O Alquimista - short (5)/O Alquimista - short - Paulo Coelho.epub
            epub_paths = {
                "br": epub_folder_path
                / "O Alquimista - short (5)"
                / "O Alquimista - short - Paulo Coelho.epub",
                "en": epub_folder_path
                / "The Alchemist - edit - short (6)"
                / "The Alchemist - edit - short - Paulo Coelho.epub",
            }
            file_name_src = "O Alquimistas"
            file_name_dst = "The Alchemist"
            file_author = "Paulo Coelho"
            file_io_src = epub_paths["br"]
            file_io_dst = epub_paths["en"]

        # set the lang tags
        ii.set_lang_tag(lt_src, "src")
        ii.set_lang_tag(lt_dst, "dst")

        # load the models
        ii.load_nlp()

        # load the books
        ii.add_book(file_io_src, "src", file_name_src, file_author)
        ii.add_book(file_io_dst, "dst", file_name_dst, file_author)

        # go forth and align
        # TODO: some way to force the align with no cache
        return redirect(url_for("align", first_align=""))

    return render_load()


@app.route("/align", methods=["GET", "POST"])
def align():
    """Align two epubs."""
    # parse POST request
    lg.debug(f"{request=}")
    if request.method == "POST":
        form_data = flatten_multidict(request.form)
        lg.debug(f"{form_data=}")
        files_data = flatten_multidict(request.files)
        lg.debug(f"{files_data=}")

    # parse GET request
    elif request.method == "GET":
        args_data = flatten_multidict(request.args)
        lg.debug(f"{args_data=}")

        if "first_align" in args_data:
            ii.align_auto()

        elif "dst_pick" in args_data:
            dst_pick = int(args_data["dst_pick"])
            ii.pick_dst_par(dst_pick)

        elif "chap_move" in args_data:
            chap_move = args_data["chap_move"]
            ii.change_chapter_curr(chap_move)

        elif "delta_move" in args_data:
            delta_move = args_data["delta_move"]
            ii.change_chapter_delta(delta_move)

        elif "ignore_cached_match" in args_data:
            ii.align_auto(force_align=True)

        elif "save_epub" in args_data:
            ii.save_epub()

    return render_align(ii)
