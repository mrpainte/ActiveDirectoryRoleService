"""Audit app URL configuration."""
from django.urls import path

from audit import views

app_name = 'audit'

urlpatterns = [
    path('', views.AuditListView.as_view(), name='list'),
    path('<int:pk>/', views.AuditDetailView.as_view(), name='detail'),
    path('export/', views.AuditExportView.as_view(), name='export'),
]
