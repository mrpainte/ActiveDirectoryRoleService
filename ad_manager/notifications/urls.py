"""Notifications app URL configuration."""
from django.urls import path

from notifications import views

app_name = 'notifications'

urlpatterns = [
    path('config/', views.NotificationConfigView.as_view(), name='config'),
    path('templates/', views.EmailTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.EmailTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.EmailTemplateEditView.as_view(), name='template_edit'),
    path('templates/<int:pk>/preview/', views.EmailTemplatePreviewView.as_view(), name='template_preview'),
    path('templates/<int:pk>/test-send/', views.EmailTemplateSendTestView.as_view(), name='template_test_send'),
    path('send/', views.SendEmailView.as_view(), name='send_email'),
    path('send/group-search/', views.GroupSearchView.as_view(), name='group_search'),
    path('history/', views.SentNotificationListView.as_view(), name='history'),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/<path:token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
