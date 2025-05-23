from django.urls import path
from .views import RefreshTokenView, LoginView, LogoutView
#from .views import CustomTokenView

urlpatterns = [
    #path('token/', CustomTokenView.as_view(), name='token'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    #path('token/anonymous/', AnonymousTokenView.as_view(), name='anonymous_token'),

    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]