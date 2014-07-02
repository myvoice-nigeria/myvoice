import datetime

from dateutil.relativedelta import relativedelta

from myvoice.clinics.models import ClinicStatistic

from .models import Survey, SurveyQuestionResponse


# Associates question label with the "positive" response.
# As we move forward, I would like to structure surveys in a way that they
# can be more predictable so that we don't have to hardcode this information
# or manually update it when a survey is imported.
_QUESTION_ANSWERS = [
    ('HospitalAvailable', 'open'),  # Was the hospital open?
    ('RespectfulStaff', 'kind'),  # Did the staff treat you with respect?
    ('CleanHospitalMaterials', 'clean'),
    ('Overcharge', 'overcharged'),
]


def analyze(month=None):
    """
    Heavily hard-coded survey analyzing code so that we can have something
    pretty to show for the sake of the pilot.
    """

    # Calculate the time period to analyze.
    month = month or datetime.datetime.today()
    start = month.replace(day=1)  # inclusive
    end = month.replace(day=1) + relativedelta(months=1)  # exclusive

    # Grab all patient feedback responses for the time period as a base.
    survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
    questions = survey.surveyquestion_set.all()
    questions = dict([(question.label, question) for question in questions])
    responses = SurveyQuestionResponse.objects.filter(
        question__survey=survey, datetime__gte=start, datetime__lt=end)

    for clinic_id in responses.values_list('clinic_id', flat=True).distinct():
        for service_id in responses.values_list('service_id', flat=True).distinct():
            filtered_responses = responses.filter(
                clinic_id=clinic_id, service_id=service_id)

            # For each clinic and service combination, determine the percentage
            # of respondents who answered positively for each question.
            for question_label, positive_response in _QUESTION_ANSWERS:
                question = questions.get(question_label)

                statistic, _ = ClinicStatistic.objects.get_or_create(
                    clinic_id=clinic_id, service_id=service_id,
                    statistic=question.statistic, month=month)
                total = filtered_responses.filter(question=question)
                positive = total.filter(response__iexact=positive_response)
                statistic.n = total.count()
                if statistic.n:
                    statistic.value = float(positive.count()) / statistic.n
                statistic.save()
