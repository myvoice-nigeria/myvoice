from django.views.generic import View

# from myvoice.core.utils import get_week_start, get_week_end, make_percentage
# from myvoice.survey import utils as survey_utils
# from myvoice.survey.models import Survey

# from . import forms
# from . import models


class AnalystSummary(View):
    template_name = 'analysts/analyst.html'

    def dispatch(self, *args, **kwargs):
        return super(AnalystSummary, self).dispatch(*args, **kwargs)
        # resp = HttpResponse("fnord")
        # return resp
