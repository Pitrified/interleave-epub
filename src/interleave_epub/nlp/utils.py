"""Misc functions and constantr pertaining to nlp models."""

from pathlib import Path


# location of the stored spacy models
SPACY_MODELS_CACHE_DIR = Path("~/.cache/spacy_my_models").expanduser()

# location of the cached translations
TRANSLATION_PIPELINE_CACHE_DIR = Path("~/.cache/my_translations").expanduser()
