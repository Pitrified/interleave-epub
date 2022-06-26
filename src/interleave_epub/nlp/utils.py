"""Misc functions and constantr pertaining to nlp models."""

from pathlib import Path
from typing import cast

import numpy as np
from torch import Tensor
from sentence_transformers import SentenceTransformer


# location of the stored spacy models
SPACY_MODELS_CACHE_DIR = Path("~/.cache/spacy_my_models").expanduser()

# location of the cached translations
TRANSLATION_PIPELINE_CACHE_DIR = Path("~/.cache/my_translations").expanduser()


def sentence_encode_np(
    sentence_transformer: SentenceTransformer,
    sentences: list[str],
) -> np.ndarray:
    """Wrap around sentence_transformer.encode that casts the result to numpy array.

    To compute the similarity you can use::

        from sklearn.metrics.pairwise import cosine_similarity
        sim = cosine_similarity(enc0, enc1)
    """
    encodings = cast(
        Tensor,
        sentence_transformer.encode(sentences, convert_to_tensor=True),
    )
    encodings = encodings.detach().cpu().numpy()
    return encodings
