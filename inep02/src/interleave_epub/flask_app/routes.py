"""Routes for the flask app."""

from flask import render_template, request

from interleave_epub.flask_app import app


@app.route("/")
@app.route("/index")
def index():
    """Render the index page."""
    return render_template("index.html", title="Home")


@app.route("/load", methods=["GET", "POST"])
def load_ep():
    """Render the page to pick the languages and load the epubs."""
    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        print(f"{request.form=}")
        print(f"{request.files=}")
        # request.form['manu']

    lts_list = ["en", "fr", "it"]
    lt_src_sel = "fr"

    return render_template(
        "load.html",
        lts_list=lts_list,
        lt_src_sel=lt_src_sel,
    )
