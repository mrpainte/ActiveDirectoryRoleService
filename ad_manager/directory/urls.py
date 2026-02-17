"""URL configuration for the directory app."""
from django.urls import path

from . import views

app_name = 'directory'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Utilities
    path('generate-password/', views.GeneratePasswordView.as_view(),
         name='generate_password'),

    # Users
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<str:encoded_dn>/', views.UserDetailView.as_view(),
         name='user_detail'),
    path('users/<str:encoded_dn>/reset-password/',
         views.UserResetPasswordView.as_view(), name='user_reset_password'),
    path('users/<str:encoded_dn>/toggle/',
         views.UserToggleView.as_view(), name='user_toggle'),
    path('users/<str:encoded_dn>/unlock/',
         views.UserUnlockView.as_view(), name='user_unlock'),

    # Computers
    path('computers/', views.ComputerListView.as_view(), name='computer_list'),
    path('computers/<str:encoded_dn>/', views.ComputerDetailView.as_view(),
         name='computer_detail'),

    # Organizational Units
    path('ous/', views.OUTreeView.as_view(), name='ou_tree'),
    path('ous/children/<str:encoded_dn>/',
         views.OUChildrenView.as_view(), name='ou_children'),
    path('ous/<str:encoded_dn>/', views.OUDetailView.as_view(),
         name='ou_detail'),
]
