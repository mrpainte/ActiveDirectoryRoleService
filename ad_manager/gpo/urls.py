"""URL configuration for the gpo app."""
from django.urls import path

from gpo import views

app_name = 'gpo'

urlpatterns = [
    path('', views.GPOListView.as_view(), name='gpo_list'),
    path('<str:encoded_dn>/', views.GPODetailView.as_view(), name='gpo_detail'),
]
