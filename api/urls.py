from django.urls import path
from .views import (
	EchoView, AnonDataView, AnonDataHelloView, AnonDataGetStateView, AnonDataSetStateView, 
	AnonDataApplyTaskMethodView, WorkspaceDownloadDataView, WorkspaceTaskView,
	WorkspaceApplyTaskMethodView
)

urlpatterns = [
	path('echo/', EchoView.as_view()),

	path("anon-data/", AnonDataView.as_view()),
	path("anon-data/hello/", AnonDataHelloView.as_view()),
	path("anon-data/get-state/", AnonDataGetStateView.as_view()),
	path("anon-data/set-state/", AnonDataSetStateView.as_view()),
	path("anon-data/apply-task-method/", AnonDataApplyTaskMethodView.as_view()),

	path('workspace/download-data/', WorkspaceDownloadDataView.as_view()),
	path('workspace/task/', WorkspaceTaskView.as_view()),
	path("workspace/apply-task-method/", WorkspaceApplyTaskMethodView.as_view()),
]
