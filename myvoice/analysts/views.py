from itertools import groupby
import json
from operator import attrgetter
from django_xhtml2pdf.utils import generate_pdf

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView

from myvoice.core.utils import get_week_start, get_week_end, make_percentage
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import Survey

#from . import forms
from . import models


class AnalystSummary(View):
    def dispatch(self, *args, **kwargs):
        resp = HttpResponse("fnord")
        return resp
