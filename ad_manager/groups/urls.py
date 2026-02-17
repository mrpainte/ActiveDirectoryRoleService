"""URL configuration for the groups app."""
from django.urls import path

from groups import views

app_name = 'groups'

urlpatterns = [
    path('', views.GroupListView.as_view(), name='group_list'),
    path('my-groups/', views.MyGroupsView.as_view(), name='my_groups'),
    path('delegation/', views.DelegationListView.as_view(), name='delegation_list'),
    path('delegation/create/', views.DelegationCreateView.as_view(), name='delegation_create'),
    path('delegation/<int:pk>/assign/', views.DelegationAssignView.as_view(), name='delegation_assign'),
    path('<str:encoded_dn>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('<str:encoded_dn>/add-member/', views.GroupAddMemberView.as_view(), name='group_add_member'),
    path('<str:encoded_dn>/remove-member/', views.GroupRemoveMemberView.as_view(), name='group_remove_member'),
]
