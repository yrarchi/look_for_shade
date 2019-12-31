from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import MapForm
from .sunlight.main import sunlight


class MapView(TemplateView):
    def __init__(self):
        self.params = {
            "name" : "Sunlight α版",
            "title" : "input",
            "form" : MapForm()}

    def get(self, request):
        return render(request, "app_sunlight/index.html", self.params)

    def post(self, request):
        self.params["title"] = "output"
        self.params["form"] = MapForm(request.POST)
        form = MapForm(request.POST)
        if form.is_valid():
            origin_lon = form.cleaned_data["origin_lon"]
            origin_lat = form.cleaned_data["origin_lat"]
            dest_lon = form.cleaned_data["dest_lon"]
            dest_lat = form.cleaned_data["dest_lat"]
            date = form.cleaned_data["date"]
            time = form.cleaned_data["time"]
            self.params["result"] = sunlight(date, time, origin_lat, origin_lon, dest_lat, dest_lon)
        return render(request, "app_sunlight/index.html", self.params)
