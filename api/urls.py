from django.urls import path
from .views import EchoView, AnonDataView, AnonDataHelloView

urlpatterns = [
	path('echo/', EchoView.as_view()),

	path("anon-data/", AnonDataView.as_view()),
	path("anon-data/hello/", AnonDataHelloView.as_view()),
]
