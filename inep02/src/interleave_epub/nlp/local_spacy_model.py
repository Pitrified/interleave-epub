"""Load cached local spacy models."""
from pathlib import Path

import spacy
from spacy.cli.download import download


def spacy_load_local_model(
    model_path: str,
    cache_dir: Path,
    force_download: bool = False,
) -> spacy.language.Language:
    """Load local spacy models from a single location.

    https://stackoverflow.com/a/67750919

    Args:
        model_path (str): Name of the model, compatible with
            ``nlp = spacy.load(model_path)``.
        cache_dir (Path): Folder to search the models in.

    Returns:
        spacy.language.Language: Loaded model.
    """
    if not cache_dir.exists():
        Path.mkdir(cache_dir, parents=True)

    try:
        if force_download is True:
            raise OSError
        # try to load from local cache
        nlp = spacy.load(cache_dir / model_path)
    except OSError:
        # download using spacy.cli
        # this model is not installed with pip and spacy.load complains
        download(model_path)
        # load with spacy.load
        nlp = spacy.load(model_path)
        # save to disk
        nlp.to_disk(cache_dir / model_path)

    return nlp
