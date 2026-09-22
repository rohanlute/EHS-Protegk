from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """
    Return mapping[key] in templates.

    Usage:
        {{ my_dict|get_item:some_variable }}

    Safe on missing keys and non-dict values.
    """
    if mapping is None:
        return ""
    try:
        return mapping.get(key, "")
    except AttributeError:
        # Not a dict — try getattr as fallback
        return getattr(mapping, key, "")


@register.filter
def get_item_or_default(mapping, key, default=""):
    """Same as get_item but with custom default."""
    if mapping is None:
        return default
    try:
        return mapping.get(key, default)
    except AttributeError:
        return getattr(mapping, key, default)