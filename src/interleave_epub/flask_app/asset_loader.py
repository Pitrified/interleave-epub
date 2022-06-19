"""Functions to load heavy assets."""
from transformers.pipelines import pipeline
from interleave_epub.flask_app import gs


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


def constants_loader():
    """Load a bunch of useful constants in the global object."""
    # if one constant is there, all are there
    if "sd_to_lang" in gs:
        return

    # src or dst
    gs["sods"] = ("src", "dst")

    # map sd to language tags
    gs["sd_to_lang"] = {"src": "fr", "dst": "en"}
