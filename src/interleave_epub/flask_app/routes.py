"""Routes for the flask app."""
from pprint import pprint
import zipfile
from flask import render_template, request
from interleave_epub.flask_app import app, gs
from interleave_epub.flask_app.asset_loader import (
    constants_loader,
    pipe_loader,
    spacy_loader,
)
from werkzeug.datastructures import FileStorage


@app.route("/")
@app.route("/index")
def index():
    """Render the index page."""
    # pipe_loader()
    print(gs)

    # lt = "en"
    # lt_other = "fr"
    # pipe_key = f"pipe_{lt}_{lt_other}"
    # tran = gs[pipe_key]("Does the pipeline work for translation tasks?")
    # print(f"translation {tran}")
    return render_template("index.html", title="Home")


@app.route("/test_route")
def test_route():
    """Test route to test things."""
    print("Testing start")
    constants_loader()
    pipe_loader()

    pprint(gs)

    tran = gs["pipe_cache"]["fr-en"]("Je ne parle pas français.")
    print(f"translation '{tran}'")

    return "Testing things."


@app.route("/load", methods=["GET", "POST"])
def epub_load():
    """Load two epubs."""
    constants_loader()

    file_names_key = "file_names"

    # file_src_key = "file-src"
    # file_dst_key = "file-dst"

    # get the data from global storage
    if file_names_key in gs:
        file_names = gs[file_names_key]
    else:
        file_names = {sod: "Still to be loaded" for sod in gs["sods"]}

    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        print(f"{request.form=}")
        print(f"{request.files=}")

        for sod in gs["sods"]:
            # build the key used in the html form
            file_form_key = f"file-{sod}"
            if file_form_key in request.files:
                # get the FileStorage
                uploaded_file: FileStorage = request.files[file_form_key]

                # get the file name
                # MAYBE werzkug safe name?
                file_name = uploaded_file.filename

                # check that the file has a valid name
                if file_name is None or file_name == "":
                    # return render_template("file_loader.html", file_names=file_names)
                    # something failed so we exit the loop: the else will catch us
                    break

                zf = zipfile.ZipFile(uploaded_file.stream)
                print(zf.namelist())

                # save the file name
                file_names[sod] = file_name
                break

        # if no one broke, the else is called
        else:
            print(f"Else of the for on the forms.")
            return render_template("file_loader.html", file_names=file_names)

    gs[file_names_key] = file_names

    return render_template("file_loader.html", file_names=file_names)


@app.route("/align", methods=["GET", "POST"])
def epub_align():
    """Align two epubs."""
    constants_loader()
    spacy_loader()
    doc = gs["nlp"][gs["lts"][0]]("Spacy is a fancy model. It can do many things.")
    print(doc)
    return "Ready to align."
