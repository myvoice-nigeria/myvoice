from django import template

from myvoice.survey.models import SurveyQuestionResponse

register = template.Library()


@register.simple_tag
def get_rate(label, question_type, service="", clinic="", start_date="", end_date=""):
    rate_query = SurveyQuestionResponse.objects.filter(
        question__label__iexact=label,
        question__question_type__iexact=question_type)

    if service:
        rate_query = rate_query.filter(service__name__iexact=service)
    if clinic:
        rate_query = rate_query.filter(clinic__name__iexact=clinic)
    if start_date:
        rate_query = rate_query.filter(visit_time__gte=start_date)
    if end_date:
        rate_query = rate_query.filter(visit_time__lte=end_date)

    return rate_query.count()

