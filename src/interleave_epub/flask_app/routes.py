"""Routes for the flask app."""
import io
import json
from pathlib import Path
from pprint import pprint
from typing import IO, Optional
import zipfile

from flask import redirect, render_template, request, url_for
from matplotlib import pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.datastructures import FileStorage

from interleave_epub.epub.chapter import Chapter
from interleave_epub.epub.epub import EPub
from interleave_epub.epub.similarity import match_similarity
from interleave_epub.flask_app import app, gs
from interleave_epub.flask_app.asset_loader import (
    constants_loader,
    epub_loader,
    pipe_loader,
    sent_transformer_loader,
    spacy_loader,
)
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
    sents_psid_src_orig = []
    for k, sent in chap_selected[lt_src].enumerate_sents(which_sent="orig"):
        text_src = sent.text
        sents_text_src_orig.append(text_src)
        sents_psid_src_orig.append(k)
    sents_len_src_orig = [len(d) for d in chap_selected[lt_src].sents_doc_orig]

    sents_text_dst_orig = []
    sents_psid_dst_orig = []
    for k, sent in chap_selected[lt_dst].enumerate_sents(which_sent="orig"):
        text_dst = sent.text
        sents_text_dst_orig.append(text_dst)
        sents_psid_dst_orig.append(k)
    sents_len_dst_orig = [len(d) for d in chap_selected[lt_dst].sents_doc_orig]
    sents_text_dst_tran = []
    sents_psid_dst_tran = []
    for k, sent in chap_selected[lt_dst].enumerate_sents(which_sent="tran"):
        text_dst_tran = sent.text
        sents_text_dst_tran.append(text_dst_tran)
        sents_psid_dst_tran.append(k)
    sents_len_dst_tran = [len(d) for d in chap_selected[lt_dst].sents_doc_tran]

    # dump them for later,
    # developing is still slow as the app gets reloaded anyway
    sents_info = {
        "sents_text_src_orig": sents_text_src_orig,
        "sents_text_dst_orig": sents_text_dst_orig,
        "sents_text_dst_tran": sents_text_dst_tran,
        "sents_psid_src_orig": sents_psid_src_orig,
        "sents_psid_dst_orig": sents_psid_dst_orig,
        "sents_psid_dst_tran": sents_psid_dst_tran,
        "sents_len_src_orig": sents_len_src_orig,
        "sents_len_dst_orig": sents_len_dst_orig,
        "sents_len_dst_tran": sents_len_dst_tran,
    }
    sents_info_path = Path("sents_info.json")
    sents_info_path.write_text(json.dumps(sents_info, indent=4))

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
    sim_fig_str = fig2imgb64str(fig)
    # print(f"{sim_fig_str=}")

    return render_template("align.html", sim_plot=sim_fig_str)


@app.route("/align_cache", methods=["GET", "POST"])
@app.route("/align_cache/<signed_int:btn>", methods=["GET", "POST"])
def epub_align_cache(btn=-99, btn2=-90):
    """Align manually a chapter, but cache the starting point."""
    # parse POST request
    if request.method == "POST":
        print(f"{request=}")
    if request.method == "GET":
        print(f"GET {request=}")
        print(f"GET {request.args=}")
    print(f"{btn=} {btn2=}")

    # reload the sentences and some info on the ids
    sents_info_path = Path("sents_info.json")
    sents_info = json.loads(sents_info_path.read_text())
    sents_text_src_orig = sents_info["sents_text_src_orig"]
    sents_psid_src_orig = sents_info["sents_psid_src_orig"]
    sents_text_dst_orig = sents_info["sents_text_dst_orig"]
    sents_psid_dst_orig = sents_info["sents_psid_dst_orig"]
    sents_text_dst_tran = sents_info["sents_text_dst_tran"]
    sents_psid_dst_tran = sents_info["sents_psid_dst_tran"]
    sents_len_src_orig = sents_info["sents_len_src_orig"]
    sents_len_dst_orig = sents_info["sents_len_dst_orig"]
    sents_len_dst_tran = sents_info["sents_len_dst_tran"]

    # load the sentence transformer
    constants_loader()
    sent_transformer_loader()
    sent_transformer = gs["sent_transformer"]
    sent_transformer_lt = "en"

    # encode them
    enc_en_orig = sentence_encode_np(
        sent_transformer[sent_transformer_lt], sents_text_src_orig
    )
    enc_fr_tran = sentence_encode_np(
        sent_transformer[sent_transformer_lt], sents_text_dst_tran
    )

    # compute the similarity
    sim = cosine_similarity(enc_en_orig, enc_fr_tran)

    # plot it for fun
    fig, ax = plt.subplots()
    ax.imshow(sim)
    ax.set_title(f"Similarity *en* vs *fr_translated*")
    ax.set_ylabel("en")
    ax.set_xlabel("fr_tran")
    # plt.show()
    sim_fig_str = fig2imgb64str(fig)
    # print(f"{sim_fig_str=}")

    print("Matching sim")

    fig_match, all_i, all_max_flattened = match_similarity(
        sim, sents_len_src_orig, sents_len_dst_tran
    )
    match_fig_str = fig2imgb64str(fig_match)

    is_ooo_flattened = []

    for j, (good_i, good_max_rescaled) in enumerate(zip(all_i, all_max_flattened)):

        # check for out of order ids
        ooo = False

        if j == 0:
            # only check to the right for the first value
            if good_max_rescaled > all_max_flattened[j + 1]:
                ooo = True
        elif j == len(all_max_flattened) - 1:
            # only check to the left for the last value
            if good_max_rescaled < all_max_flattened[j - 1]:
                ooo = True
        else:
            if (
                good_max_rescaled > all_max_flattened[j + 1]
                or good_max_rescaled < all_max_flattened[j - 1]
            ):
                ooo = True

        if ooo:
            print(j, good_i, good_max_rescaled)

        is_ooo_flattened.append(ooo)

    # print("Search ooo")
    # for j in range(len(is_ooo_flattened)):
    #     if is_ooo_flattened[j]:
    #         print(f"{j} is ooo")

    first_ooo = is_ooo_flattened.index(True)
    sent_win_len = 5

    # get the mean of neighboring all_max_flattened as possible match for first_ooo (i)
    # and use that mean as center in the info_zip for french right side sentences ids

    # for ir in range(-winlen, winlen)
    # en[first_ooo+ir]
    # fr[mean_max+ir]

    info_zip = []
    for i in range(first_ooo - sent_win_len, first_ooo + sent_win_len):
        assert all_i[i] == i
        info_zip.append(
            (
                sents_text_src_orig[i],
                sents_text_dst_orig[i],
                i,
                i - 5,
            )
        )

    highlight_id = first_ooo
    print(f"{all_max_flattened[highlight_id]=}")

    return render_template(
        "align.html",
        sim_plot=sim_fig_str,
        match_plot=match_fig_str,
        info_zip=info_zip,
        highlight_id=highlight_id,
    )
