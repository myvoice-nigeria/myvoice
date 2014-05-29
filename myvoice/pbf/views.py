from django.views.generic import TemplateView


class PBFDashboard(TemplateView):
    template_name = 'pbf/dashboard.html'
