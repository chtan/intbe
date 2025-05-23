from django.urls import path
from .views import EchoView, AnonDataView

urlpatterns = [
	path('echo/', EchoView.as_view()),
	path("anon-data/", AnonDataView.as_view()),
]
