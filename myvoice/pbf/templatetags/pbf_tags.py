from django import template


register = template.Library()


@register.simple_tag
def get_rank_class(rank, total, good=0.7):
    """
    If the rank is in the given percentile, it is considered good.
    """
    rank_percentile = 1.0 - float(rank) / float(total)
    if rank_percentile >= good:
        return 'good-rank'
    else:
        return 'bad-rank'
