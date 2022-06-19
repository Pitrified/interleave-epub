"""Routes for the flask app."""
import io
from pprint import pprint
from typing import IO, Optional
import zipfile
from flask import redirect, render_template, request, url_for
from interleave_epub.epub.epub import EPub
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
    spacy_loader()
    pipe_loader()

    pprint(gs)

    doc = gs["nlp"][gs["lts"][0]]("Spacy is a fancy model. It can do many things.")
    print(doc)
    tran = gs["pipe_cache"][gs["lts_pair_h"][0]]("Je ne parle pas français.")
    print(f"translation '{tran}'")

    return "Testing things."


@app.route("/load", methods=["GET", "POST"])
def epub_load():
    """Load two epubs."""
    constants_loader()

    # get the data from global storage

    file_names_key = "file_names"
    if file_names_key in gs:
        file_names = gs[file_names_key]
    else:
        file_names = {sod: "Still to be loaded" for sod in gs["sods"]}

    file_content_key = "file_content"
    if file_content_key in gs:
        file_content = gs[file_content_key]
    else:
        file_content: dict[str, Optional[IO[bytes]]] = {sod: None for sod in gs["sods"]}

    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
        print(f"{request.form=}")
        print(f"{request.files=}")

        # iterate over the two forms
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

                # uploaded_file.stream is a SpooledTemporaryFile:
                # read the contents as bytes
                file_bytes_content = uploaded_file.stream.read()
                # convert the bytes back to a stream
                file_io_stream = io.BytesIO(file_bytes_content)

                # save the file name
                file_names[sod] = file_name
                # save the file content
                file_content[sod] = file_io_stream
                break

        # if no one broke, the else is called
        else:
            print(f"Else of the for on the forms.")
            return render_template("file_loader.html", file_names=file_names)

    gs[file_names_key] = file_names
    gs[file_content_key] = file_content

    return render_template("file_loader.html", file_names=file_names)


@app.route("/align", methods=["GET", "POST"])
def epub_align():
    """Align two epubs."""
    if "file_content" not in gs or any(f is None for f in gs["file_content"].values()):
        print("Redirecting back to load")
        return redirect(url_for("epub_load"))

    constants_loader()
    spacy_loader()
    pipe_loader()

    if "epub" not in gs:
        print("Loading epubs for the first time")
        gs["epub"] = {
            lt: EPub(
                gs["file_content"][gs["lang_to_sd"][lt]],
                gs["nlp"],
                gs["pipe_cache"],
                lt,
                lt_other,
            )
            for lt, lt_other in gs["lts_pair_t"]
        }
        print("Loading done")

    return "Ready to align."
