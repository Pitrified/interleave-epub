"""Functions to load heavy assets."""
from pathlib import Path
from typing import cast

from sentence_transformers import SentenceTransformer
from transformers.pipelines import pipeline
from transformers.pipelines.text2text_generation import TranslationPipeline

from interleave_epub.epub.epub import EPub
from interleave_epub.flask_app import gs
from interleave_epub.nlp.cached_pipe import TranslationPipelineCache
from interleave_epub.nlp.cached_spacy import spacy_load_cached
from interleave_epub.nlp.utils import (
    SPACY_MODELS_CACHE_DIR,
    TRANSLATION_PIPELINE_CACHE_DIR,
)


def pipe_loader():
    """Load a pipeline and store it in the session object.

    pipeline is a transformers.pipelines.text2text_generation.TranslationPipeline
    """
    if "pipe_cache" in gs:
        return
    print("Loading hug")

    # pipe_key = f"pipe_{lt}_{lt_other}"
    # if pipe_key not in gs:
    #     print(f"Loading to global state")
    #     gs[pipe_key] = pipeline(
    #         "translation", model=f"Helsinki-NLP/opus-mt-{lt}-{lt_other}"
    #     )

    load_pipeline = gs["load_pipeline"]
    pipe_cache_paths = gs["pipe_cache_paths"]
    pipe_model_names = gs["pipe_model_names"]

    # load the pipeline if requested in load_pipeline
    gs["pipe"] = {
        lt_pair: cast(
            TranslationPipeline,
            pipeline("translation", model=pipe_model_names[lt_pair]),
        )
        if load_pipeline[lt_pair]
        else None
        for lt_pair in gs["lts_pair_h"]
    }

    # load the cached pipeline
    gs["pipe_cache"] = {
        lt_pair: TranslationPipelineCache(
            gs["pipe"][lt_pair], pipe_cache_paths[lt_pair], lt_pair=lt_pair
        )
        for lt_pair in gs["lts_pair_h"]
    }


def spacy_loader():
    """Load spacy models from system cache folder."""
    if "nlp" in gs:
        return
    print("Loading spacy")
    lts = gs["lts"]
    spacy_model_names = gs["spacy_model_names"]
    gs["nlp"] = {
        lt: spacy_load_cached(spacy_model_names[lt], SPACY_MODELS_CACHE_DIR)
        for lt in lts
    }


def sent_transformer_loader():
    """Load the sentence transformer."""
    print("Loading sentence transformer")
    if "sent_transformer" in gs:
        return
    gs["sent_transformer"] = {
        "en": SentenceTransformer(gs["sent_model_names"]["en"], device="cpu")
    }


def constants_loader():
    """Load a bunch of useful constants in the global object."""
    # if one constant is there, all are there
    if "sd_to_lang" in gs:
        return

    # map sd to language tags
    gs["sd_to_lang"] = {"src": "en", "dst": "fr"}
    gs["lang_to_sd"] = {v: k for k, v in gs["sd_to_lang"].items()}

    # src or dst
    gs["sods"] = tuple(gs["sd_to_lang"].keys())

    # language tags
    gs["lts"] = tuple(gs["sd_to_lang"].values())
    # tuple
    gs["lts_pair_t"] = list(zip(gs["lts"], gs["lts"][::-1]))
    # underscore
    gs["lts_pair_u"] = [f"{lt}_{lt_other}" for lt, lt_other in gs["lts_pair_t"]]
    # hyphen
    gs["lts_pair_h"] = [f"{lt}-{lt_other}" for lt, lt_other in gs["lts_pair_t"]]

    # spacy model names
    gs["spacy_model_names"] = {
        "en": "en_core_web_md",
        "fr": "fr_core_news_md",
    }

    # true to load the translation pipeline
    # false to hope we have cached some translations
    # it is mildly insane but Helsinki-NLP use hyphens so we also use hyphens
    gs["load_pipeline"] = {
        "en-fr": False,
        "fr-en": True,
    }

    # file with cached translations
    gs["pipe_cache_paths"] = {
        lt_pair: TRANSLATION_PIPELINE_CACHE_DIR / f"{lt_pair}.json"
        for lt_pair in gs["lts_pair_h"]
    }

    # huggingface model names
    gs["pipe_model_names"] = {
        lt_pair: f"Helsinki-NLP/opus-mt-{lt_pair}" for lt_pair in gs["lts_pair_h"]
    }

    # sentence transformer model names
    gs["sent_model_names"] = {
        "en": "sentence-transformers/all-MiniLM-L6-v2",
    }


def epub_loader():
    """Load the epubs in memory and translate them."""
    if "epub" in gs:
        return
    print("Loading epubs")
    # this tasty piece of spaghetti converts language tag to src,
    # as that is the key in the file_content
    # MAYBE clearly it is better to convert sod in langtag inside load
    # gs["file_content"][gs["lang_to_sd"][lt]],
    #                     |-> [ fr -> src ]
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


def cache_fol_loader():
    """Create the cache folder."""
    if "cache_fol" in gs:
        return
    print("Creating cache folder.")

    this_file_fol = Path(__file__).absolute().parent
    print(f"{this_file_fol=}")

    package_root_fol = this_file_fol.parent.parent.parent
    print(f"{package_root_fol=}")

    cache_fol = package_root_fol / "cache"
    print(f"{cache_fol=}")
    if not cache_fol.exists():
        cache_fol.mkdir()
    gs["cache_fol"] = cache_fol
