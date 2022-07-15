"""Routes for the flask app."""
import io
import json
from pathlib import Path
from pprint import pprint
from typing import IO, Optional
import zipfile

from flask import redirect, render_template, request, url_for
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.datastructures import FileStorage
from interleave_epub.epub.build_aligned_chap import build_aligned_epub

from interleave_epub.epub.chapter import Chapter
from interleave_epub.epub.epub import EPub
from interleave_epub.epub.similarity import match_similarity
from interleave_epub.flask_app import app, gs
from interleave_epub.flask_app.asset_loader import (
    cache_fol_loader,
    constants_loader,
    epub_loader,
    pipe_loader,
    sent_transformer_loader,
    spacy_loader,
)
from interleave_epub.flask_app.utils import fig2imgb64str
from interleave_epub.nlp.utils import sentence_encode_np
from interleave_epub.utils import is_index_valid, validate_index


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
    print(f"\n----- align -----")

    ###################################################################
    # check that we have files to load
    if "file_content" not in gs or any(f is None for f in gs["file_content"].values()):
        print("Redirecting back to load")
        return redirect(url_for("epub_load"))

    ###################################################################
    # load misc global state
    constants_loader()
    cache_fol_loader()
    spacy_loader()
    pipe_loader()

    sent_transformer_loader()
    sent_transformer = gs["sent_transformer"]
    sent_transformer_lt = "en"

    # for mild sanity extract some values
    lt_src: str = gs["sd_to_lang"]["src"]
    lt_dst: str = gs["sd_to_lang"]["dst"]
    lts: dict[str, str] = gs["lts"]

    ###################################################################
    # build the epubs
    epub_loader()
    epub: dict[str, EPub] = gs["epub"]

    ###################################################################
    # chapter ids to align, set with some forms in an intermediate page
    # MAYBE some align_setup
    chap_id_start = {lt: 0 for lt in gs["lts"]}
    gs["chap_id_start"] = chap_id_start
    # then we add delta
    chap_curr_delta = 0
    gs["chap_curr_delta"] = chap_curr_delta
    chap_id = {lt: chap_id_start[lt] + chap_curr_delta for lt in gs["lts"]}

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

    # FIXME a whole bunch of this is already inside the EPub object
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
    sents_info_path = Path(f"sents_info_{chap_curr_delta}.json")
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
# @app.route("/align_cache/<signed_int:btn>", methods=["GET", "POST"])
def epub_align_cache(btn=-99, btn2=-90):
    """Align manually a chapter, but cache the starting point."""
    print(f"\n----- align_cache -----")

    ###################################################################
    # parse POST request
    req_arg = {}
    if request.method == "POST":
        print(f"{request=}")
    if request.method == "GET":
        print(f"GET {request=}")
        print(f"GET {request.args=}")
        # flatten the multidict who cares
        req_arg = {k: request.args[k] for k in request.args}
    print(f"{req_arg}")

    ###################################################################
    # load state
    constants_loader()
    cache_fol_loader()

    ###################################################################
    # indexes of the chapters
    # somewhere someone found this values
    # that is, the index of the first real chap we need to analyze
    chap_id_start = {lt: 0 for lt in gs["lts"]}
    gs["chap_id_start"] = chap_id_start

    # then we add delta:
    # if we know the delta
    if "chap_curr_delta" in gs:
        # and want to move it
        if "chap_move" in req_arg:
            chap_old_delta = gs["chap_curr_delta"]
            if req_arg["chap_move"] == "back":
                gs["chap_curr_delta"] -= 1
            elif req_arg["chap_move"] == "forward":
                gs["chap_curr_delta"] += 1
            chap_tot_num = 2
            gs["chap_curr_delta"] = validate_index(
                gs["chap_curr_delta"], list(range(chap_tot_num))
            )
            # if the chapter changed, clean the global state from chapter specific data
            if chap_old_delta != gs["chap_curr_delta"]:
                gs.pop("sents_info", 0)
                gs.pop("all_i", 0)
                gs.pop("fixed_src_i_set", 0)
                gs.pop("curr_i_src", 0)
    # initialize the delta if we don't know it
    else:
        gs["chap_curr_delta"] = 0
    # save it outside gs for ease of use
    chap_curr_delta = gs["chap_curr_delta"]
    # build the chap id for each epub
    chap_id = {lt: chap_id_start[lt] + chap_curr_delta for lt in gs["lts"]}
    
    ###################################################################
    # reload the sentences and some info on the ids
    # this whole thing is actually already inside EPubs, this is just caching
    # if it is the first time loading the cache
    if "sents_info" not in gs:
        sents_info_path = Path(f"sents_info_{chap_curr_delta}.json")
        sents_info = json.loads(sents_info_path.read_text())
        gs["sents_info"] = sents_info
    # or just extract it from the global state (barf)
    else:
        sents_info = gs["sents_info"]

    sents_text_src_orig = sents_info["sents_text_src_orig"]
    sents_psid_src_orig = sents_info["sents_psid_src_orig"]
    sents_text_dst_orig = sents_info["sents_text_dst_orig"]
    sents_psid_dst_orig = sents_info["sents_psid_dst_orig"]
    sents_text_dst_tran = sents_info["sents_text_dst_tran"]
    sents_psid_dst_tran = sents_info["sents_psid_dst_tran"]
    sents_len_src_orig = sents_info["sents_len_src_orig"]
    sents_len_dst_orig = sents_info["sents_len_dst_orig"]
    sents_len_dst_tran = sents_info["sents_len_dst_tran"]

    ###################################################################
    # save the interleaved epub
    if "save_epub" in req_arg and req_arg["save_epub"] == "True":
        build_aligned_epub()

    ###################################################################
    # the fixed src i
    if "fixed_src_i_set" not in gs:
        gs["fixed_src_i_set"] = set()

    ###################################################################
    # match info cache location
    match_info_path = gs["cache_fol"] / f"match_info_{chap_curr_delta}.json"

    # button to ignore cache was pressed
    if "ignore_cached_match" in req_arg and req_arg["ignore_cached_match"] == "True":
        ignore_cached_match = True
        print(f"{ignore_cached_match=}")
    else:
        ignore_cached_match = False
        print(f"{ignore_cached_match=}")

    # if it is the first time or we want to ignore the cached data and restart
    # compute sim and hopeful matching
    if "all_i" not in gs or ignore_cached_match:

        if match_info_path.exists() and not ignore_cached_match:
            # load the cached matches
            print(f"found match info at {match_info_path}")
            match_info = json.loads(match_info_path.read_text())
            all_i = match_info["all_i"]
            all_max_flattened = match_info["all_max_flattened"]
            match_fig_str = match_info["match_fig_str"]
            sim_fig_str = match_info["sim_fig_str"]

        else:
            # load the sentence transformer
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

            # save it for later wtf I hate everything
            gs["all_i"] = all_i
            gs["all_max_flattened"] = all_max_flattened
            gs["match_fig_str"] = match_fig_str
            gs["sim_fig_str"] = sim_fig_str

    else:
        # the point is that all_max_flattened will actually change
        print(f"reloading matching from global state")
        all_i = gs["all_i"]
        all_max_flattened = gs["all_max_flattened"]
        match_fig_str = gs["match_fig_str"]
        sim_fig_str = gs["sim_fig_str"]

    ###################################################################
    # we picked a dst id to match the sentence properly
    if "dst_pick" in req_arg:
        # check we actually know what index to match it to
        if "curr_i_src" in gs:
            print(f"manual match for {gs['curr_i_src']=} {req_arg['dst_pick']=}")
            # update the matching list
            all_max_flattened[gs["curr_i_src"]] = int(req_arg["dst_pick"])
            # add the current sentence to the fixed set
            gs["fixed_src_i_set"].add(gs["curr_i_src"])

    ###################################################################
    # check for out of order ids
    is_ooo_flattened = []
    for j, (good_i, good_max_rescaled) in enumerate(zip(all_i, all_max_flattened)):
        ooo = False
        # TODO do this by validating the index, then checking the value
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

    # random constant that will be put somewhere
    sent_win_len = 10

    # interpolate the values for the ooo guesses
    amf_series = pd.Series(all_max_flattened)
    amf_series[is_ooo_flattened] = np.nan
    amf_series.interpolate(inplace=True)

    ###################################################################
    # the current sent we are fixing for src

    # manually change the src_i from a button
    # so in the request.args you see new_i_src param
    # the mean_max_i_dst will be updated accordingly
    if "curr_i_src" in gs and "src_move" in req_arg:
        if req_arg["src_move"] == "back":
            gs["curr_i_src"] -= sent_win_len
        elif req_arg["src_move"] == "forward":
            gs["curr_i_src"] += sent_win_len
        gs["curr_i_src"] = validate_index(gs["curr_i_src"], sents_text_src_orig)

    # compute it from the ooo list
    else:
        # if you already selected the correct dst_i for this src_i it should be skipped
        for fixed_src_i in gs["fixed_src_i_set"]:
            print(f"skipping {fixed_src_i=}")
            is_ooo_flattened[fixed_src_i] = False
        # find the first one to fix if it exists
        if True in is_ooo_flattened:
            gs["curr_i_src"] = is_ooo_flattened.index(True)
        else:
            gs["curr_i_src"] = 0
            print(f"Finished aligning")
            # might want to save the thing and move on to the next chapter automagically

    ###################################################################
    # the best match we have for now
    # get the mean of neighboring all_max_flattened as possible match for curr_i_src (i)
    # and use that mean as center in the info_zip for french right side sentences ids
    # mean_max_i_dst = all_max_flattened[curr_i_src]

    # if we know it, we might want to change it
    if "mean_max_i_dst" in gs and "dst_move" in req_arg:
        if req_arg["dst_move"] == "back":
            gs["mean_max_i_dst"] -= sent_win_len
        elif req_arg["dst_move"] == "forward":
            gs["mean_max_i_dst"] += sent_win_len
        gs["mean_max_i_dst"] = validate_index(gs["mean_max_i_dst"], sents_text_dst_orig)

    # if we never saw this (the first time) compute it
    # or any time we are not moving it manually
    else:
        gs["mean_max_i_dst"] = int(amf_series[gs["curr_i_src"]])

    print(f"{gs['curr_i_src']=} {amf_series[gs['curr_i_src']]=}")

    ###################################################################
    # build zipped infos for visualization
    info_zip = []
    empty_tag = "-"
    for i in range(-sent_win_len, sent_win_len):

        # src sent
        src_i = gs["curr_i_src"] + i
        if is_index_valid(src_i, sents_text_src_orig):
            print(f"validating {src_i=} {len(sents_text_src_orig)=}")
            sent_src = sents_text_src_orig[src_i]
            original_guess_dst_i = all_max_flattened[src_i]
        else:
            sent_src = empty_tag
            src_i = empty_tag
            original_guess_dst_i = empty_tag

        # dst sent
        dst_i = gs["mean_max_i_dst"] + i
        if is_index_valid(dst_i, sents_text_dst_orig):
            sent_dst = sents_text_dst_orig[dst_i]
        else:
            sent_dst = empty_tag
            dst_i = empty_tag

        # if both sentences are empty skip them
        if sent_src == empty_tag and sent_dst == empty_tag:
            continue

        info_zip.append(
            (
                sent_src,
                sent_dst,
                src_i,
                dst_i,
                original_guess_dst_i,
            )
        )

    ###################################################################
    # save the match info to resume if the app is closed
    match_info = {
        "all_i": all_i,
        "all_max_flattened": all_max_flattened,
        "match_fig_str": match_fig_str,
        "sim_fig_str": sim_fig_str,
    }
    match_info_path.write_text(json.dumps(match_info, indent=4))
    print(f"saved in {match_info_path}")

    return render_template(
        "align.html",
        sim_plot=sim_fig_str,
        match_plot=match_fig_str,
        info_zip=info_zip,
        curr_i_src=gs["curr_i_src"],
    )
