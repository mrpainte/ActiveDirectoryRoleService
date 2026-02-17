"""Django admin registration for accounts models."""
from django.contrib import admin

from accounts.models import Role, UserProfile


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'ad_group_dn')
    ordering = ('-priority',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'ad_dn', 'last_synced')
    list_select_related = ('user',)
    filter_horizontal = ('roles',)
