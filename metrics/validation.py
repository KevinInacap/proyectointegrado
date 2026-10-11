import re


def catalog_id(value):
    """Accept integer JSON IDs or their decimal string representation only."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('Se requiere un ID entero positivo.')
    text = str(value)
    if not re.fullmatch(r'[0-9]{1,19}', text) or not 0 < int(text) <= 9223372036854775807:
        raise ValueError('Se requiere un ID entero positivo.')
    return int(text)
