"""Functions to load heavy assets."""
from pathlib import Path
from transformers.pipelines import pipeline
from interleave_epub.flask_app import gs
from interleave_epub.nlp.cached_spacy import spacy_load_cached
from interleave_epub.nlp.utils import SPACY_MODELS_CACHE_DIR


def pipe_loader(lt: str = "en", lt_other: str = "fr"):
    """Load a pipeline and store it in the session object.

    pipeline is a transformers.pipelines.text2text_generation.TranslationPipeline
    """
    print(f"Loading {lt} {lt_other}")
    pipe_key = f"pipe_{lt}_{lt_other}"
    if pipe_key not in gs:
        print(f"Loading to global state")
        gs[pipe_key] = pipeline(
            "translation", model=f"Helsinki-NLP/opus-mt-{lt}-{lt_other}"
        )


def spacy_loader():
    """Load spacy models from system cache folder."""
    lts = gs["lts"]
    spacy_model_names = gs["spacy_model_names"]
    gs["nlp"] = {
        lt: spacy_load_cached(spacy_model_names[lt], SPACY_MODELS_CACHE_DIR)
        for lt in lts
    }


def constants_loader():
    """Load a bunch of useful constants in the global object."""
    # if one constant is there, all are there
    if "sd_to_lang" in gs:
        return

    # map sd to language tags
    gs["sd_to_lang"] = {"src": "fr", "dst": "en"}

    # src or dst
    gs["sods"] = tuple(gs["sd_to_lang"].keys())

    # language tags
    gs["lts"] = tuple(gs["sd_to_lang"].values())
    # tuple
    gs["lts_pair_t"] = list(zip(gs["lts"], gs["lts"][::-1]))
    # underscore
    gs["lts_pair_u"] = [f"{lt}_{lt_other}" for lt, lt_other in gs["lts_pair_t"]]
    # hyphen
    gs["lts_pair_h"] = [f"{lt}_{lt_other}" for lt, lt_other in gs["lts_pair_t"]]

    # model names
    gs["spacy_model_names"] = {
        "en": "en_core_web_md",
        "fr": "fr_core_news_md",
    }
