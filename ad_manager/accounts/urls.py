"""URL configuration for the accounts app."""
from django.urls import path

from accounts.views import LoginView, logout_view

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
]
