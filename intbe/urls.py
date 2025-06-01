"""
URL configuration for intbe project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from home import views as home_views
from workspace import views as workspace_views
from task import views as task_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('welcome/echo', home_views.echo),

    #path('workspace/<str:uid>', workspace_views.index),
    path('workspace/', workspace_views.index),
    path('workspace/task/', workspace_views.task),
    path('workspace/update_state', workspace_views.update_state),
    path('workspace/download_data', workspace_views.download_data),
    
    path('task/', task_views.index),
    path('task/update_state', task_views.update_state),
    path('task/update_state2', task_views.update_state2),
    path('task/update_state3', task_views.update_state3),
]

urlpatterns += [
    path('users/', include('users.urls')),  # prefix routes like /users/token/
    path('api/', include('api.urls')),  # prefix routes like /api/token/
]

