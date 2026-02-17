"""Forms for group management."""
from django import forms

from groups.models import DelegatedGroup, GroupManagerAssignment


class AddMemberForm(forms.Form):
    """Form for adding a member to a group."""

    member_dn = forms.CharField(widget=forms.HiddenInput())


class DelegatedGroupForm(forms.ModelForm):
    """Form for creating/editing a delegated group."""

    class Meta:
        model = DelegatedGroup
        fields = ['group_dn', 'display_name', 'description', 'enabled']
        widgets = {
            'group_dn': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CN=GroupName,OU=Groups,DC=example,DC=com',
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class GroupManagerAssignmentForm(forms.ModelForm):
    """Form for assigning a manager to a delegated group."""

    class Meta:
        model = GroupManagerAssignment
        fields = ['user']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
        }
