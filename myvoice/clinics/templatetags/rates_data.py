from django import template

register = template.Library()


class GetRateNode(template.Node):
    def __init__(self, qset, label, question_type):
        self.qset = template.Variable(qset)
        self.label = label
        self.question_type = question_type

    def render(self, context):
        qset = self.qset.resolve(context)
        return qset.filter(
            question__label__iexact=self.label,
            question__question_type__iexact=self.question_type).count()


@register.tag
def get_rate(parser, token):
    try:
        tag_name, qset, label, question_type = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r tag requires exactly three arguments')
    return GetRateNode(qset, label[1:-1], question_type[1:-1])
