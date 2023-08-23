"""Misc functions and constants pertaining to EPubs."""

from bs4 import Tag

VALID_CHAP_EXT = [".xhtml", ".xml", ".html"]


def tag_add_attr_multi_valued(tag: Tag, attr_name: str, attr_value: str):
    """Add a value to a multi valued attribute to a tag, safely."""
    tag[attr_name] = tag.get(attr_name, []) + [attr_value]
