"""URL configuration for the dns_manager app."""
from django.urls import path

from dns_manager import views

app_name = 'dns_manager'

urlpatterns = [
    path('', views.ZoneListView.as_view(), name='zone_list'),
    path('<str:encoded_dn>/', views.RecordListView.as_view(), name='record_list'),
    path('<str:encoded_dn>/create/', views.RecordCreateView.as_view(), name='record_create'),
    path('record/<str:encoded_dn>/edit/', views.RecordEditView.as_view(), name='record_edit'),
    path('record/<str:encoded_dn>/delete/', views.RecordDeleteView.as_view(), name='record_delete'),
]
