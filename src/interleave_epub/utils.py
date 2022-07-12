"""General utils for the whole package."""


from typing import Any, Optional


def validate_index(
    index: int,
    list_: list[Any],
    allow_negative_index: bool = False,
) -> int:
    """Validate an index so that it is valid for a list."""
    len_list = len(list_)
    min_index = -len_list if allow_negative_index else 0
    if min_index <= index < len_list:
        return index
    if index >= len_list:
        return len_list
    return min_index


def is_index_valid(
    index: int,
    list_: list[Any],
    allow_negative_index: bool = False,
) -> bool:
    """Return true if the index is valid."""
    valid_index = validate_index(index, list_, allow_negative_index)
    if valid_index == index:
        return True
    return False
