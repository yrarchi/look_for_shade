#from django.urls import path
#from . import views
from .views import MapView
from django.conf.urls import url

urlpatterns = [
    url(r"", MapView.as_view(), name="index"),
]
