"""Constants related to the app."""


from pathlib import Path

################################################################################
# NLP

spa_model_names = {
    # "en": "en_core_web_md",
    # "fr": "fr_core_news_md",
    "en": "en_core_web_sm",
    "fr": "fr_core_news_sm",
}
spa_model_cache_fol = Path("~/.cache/spacy_my_models").expanduser()

hug_trad_file_tmpl = "translated_{}.json"
hug_trad_cache_fol = Path("~/.cache/hug_my_trad").expanduser()
hug_model_name_tmpl = "Helsinki-NLP/opus-mt-{}"
# hug_model_names = {
#     lt_pair: f"Helsinki-NLP/opus-mt-{lt_pair}" for lt_pair in lts_pair_h
# }

# sentence transformer model names
sent_model_names = {
    "en": "sentence-transformers/all-MiniLM-L6-v2",
}

################################################################################
# default values for the view

# language tags
lt_options = [
    {"tag": "auto", "name": "Auto detect"},
    {"tag": "en", "name": "English"},
    {"tag": "fr", "name": "French"},
]
lt_src_default = "fr"
lt_dst_default = "en"
