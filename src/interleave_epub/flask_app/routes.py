"""Routes for the flask app."""
import io
from pprint import pprint
from typing import IO, Optional
import zipfile

from flask import redirect, render_template, request, url_for
from matplotlib import pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity

from interleave_epub.epub.chapter import Chapter
from interleave_epub.epub.epub import EPub
from interleave_epub.flask_app import app, gs
from interleave_epub.flask_app.asset_loader import (
    constants_loader,
    epub_loader,
    pipe_loader,
    sent_transformer_loader,
    spacy_loader,
)
from werkzeug.datastructures import FileStorage
from interleave_epub.flask_app.utils import fig2imgb64str

from interleave_epub.nlp.utils import sentence_encode_np


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
                    # this is spaghetti of the finest quality
                    # we break here, don't update the file_names/content,
                    # place them in globals anyway, render the template
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
                # we also break here, the else is skipped and we update globals with the new data
                break

        # if no one broke, the else is called
        # which means that for some reason the form in the request
        # was not one registered with the key
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

    sent_transformer_loader()
    sent_transformer = gs["sent_transformer"]
    sent_transformer_lt = "en"

    # for mild sanity
    lt_src: str = gs["sd_to_lang"]["src"]
    lt_dst: str = gs["sd_to_lang"]["dst"]
    lts: dict[str, str] = gs["lts"]

    epub_loader()
    epub: dict[str, EPub] = gs["epub"]

    # chapter ids to align, set with some forms in an intermediate page
    # MAYBE some align_setup
    chap_id = {lt: 0 for lt in gs["lts"]}

    # get the actual chapter objects
    chap_selected = {lt: epub[lt].chapters[chap_id[lt]] for lt in lts}

    sent_fr = chap_selected[lt_src].paragraphs[0].sents_orig[0]
    print(f"{sent_fr.text=}")
    sent_en = chap_selected[lt_dst].paragraphs[0].sents_tran[0]
    print(f"{sent_en.text=}")

    # we need an `active_sent_src_id`, can be set by clicking src button
    # that will be matched to the `dst_id` when clicked dst button

    # all sentences at once
    # we should bring both to en somehow
    sents_text_src_orig = []
    for k, sent in chap_selected[lt_src].enumerate_sents(which_sent="orig"):
        text_src = sent.text
        sents_text_src_orig.append(text_src)
    sents_text_dst_tran = []
    for k, sent in chap_selected[lt_dst].enumerate_sents(which_sent="tran"):
        text_dst_tran = sent.text
        sents_text_dst_tran.append(text_dst_tran)

    # encode them
    enc_en_orig = sentence_encode_np(
        sent_transformer[sent_transformer_lt], sents_text_src_orig
    )
    enc_fr_tran = sentence_encode_np(
        sent_transformer[sent_transformer_lt], sents_text_dst_tran
    )

    # compute the similarity
    sim = cosine_similarity(enc_en_orig, enc_fr_tran)
    fig, ax = plt.subplots()
    ax.imshow(sim)
    ax.set_title(f"Similarity *en* vs *fr_translated*")
    ax.set_ylabel("en")
    ax.set_xlabel("fr_tran")
    # plt.show()
    fig_sim = fig2imgb64str(fig)
    # print(f"{fig_sim=}")

    return render_template("align.html", sim_plot=fig_sim)
