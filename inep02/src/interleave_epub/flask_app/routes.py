"""Routes for the flask app."""

from flask import render_template, request

from interleave_epub.flask_app import app


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
    lt_src_sel = "fr"
    lt_dst_sel = "en"

    return render_template(
        "learn_html_01.html",
        title="Home",
        lts_list=lts_list,
        lt_src_sel=lt_src_sel,
        lt_dst_sel=lt_dst_sel,
    )


@app.route("/load", methods=["GET", "POST"])
def load_ep():
    """Render the page to pick the languages and load the epubs."""
    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        print(f"{request.form=}")
        print(f"{request.files=}")
        # request.form['manu']

    lts_list = [
        {"tag": "auto", "name": "Auto detect"},
        {"tag": "en", "name": "English"},
        {"tag": "fr", "name": "French"},
    ]
    lt_src_sel = "fr"
    lt_dst_sel = "en"

    return render_template(
        "load.html",
        lts_list=lts_list,
        lt_src_sel=lt_src_sel,
        lt_dst_sel=lt_dst_sel,
    )
