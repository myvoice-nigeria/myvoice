from django import template


register = template.Library()


@register.filter
def get_index(list, value):
    """Returns the index of `value` in the specified `list`."""
    try:
        value = '\n'.join(value.split())
        return list.index(value)
    except ValueError:
        return -1
