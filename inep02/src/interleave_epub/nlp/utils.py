"""Misc functions and constantr pertaining to nlp models."""
from pathlib import Path
from typing import cast

import numpy as np
from sentence_transformers import SentenceTransformer
from torch import Tensor


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
    encodings_np: np.ndarray = encodings.detach().cpu().numpy()
    return encodings_np
