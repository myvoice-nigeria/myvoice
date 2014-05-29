from django.shortcuts import redirect
from django.views.generic import TemplateView


class PBFDashboardSelect(TemplateView):
    template_name = 'pbf/select.html'

    def post(self, request, *args, **kwargs):
        return redirect('pbf_dashboard', 'wayo-matti')


class PBFDashboard(TemplateView):
    template_name = 'pbf/dashboard/dashboard.html'
