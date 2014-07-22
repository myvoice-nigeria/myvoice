from django import template

from myvoice.survey.models import SurveyQuestionResponse

register = template.Library()


@register.simple_tag
def get_rate(label, question_type):
    return SurveyQuestionResponse.objects.filter(
        question__label__iexact=label,
        question__question_type__iexact=question_type).count()
