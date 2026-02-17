"""Account models: Role and UserProfile."""
from django.conf import settings
from django.db import models


class Role(models.Model):
    """Maps an application role to an Active Directory group."""
    name = models.CharField(max_length=50, unique=True)
    ad_group_dn = models.TextField(
        blank=True,
        default='',
        help_text='Distinguished name of the AD group mapped to this role.',
    )
    description = models.TextField(blank=True, default='')
    priority = models.IntegerField(
        default=0,
        help_text='Higher value = more privileges.',
    )

    class Meta:
        ordering = ['-priority']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended profile linking a Django user to their AD identity."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    ad_dn = models.TextField(blank=True, default='', help_text='AD Distinguished Name')
    ad_guid = models.CharField(max_length=64, blank=True, default='', help_text='AD objectGUID')
    roles = models.ManyToManyField(Role, blank=True)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} profile"
