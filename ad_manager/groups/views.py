"""Views for group management."""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.constants import ROLE_ADMIN, ROLE_HELPDESK, ROLE_GROUP_MANAGER
from core.mixins import RoleRequiredMixin
from directory.services.base_service import LDAPServiceError, dn_to_base64, base64_to_dn
from groups.forms import AddMemberForm, DelegatedGroupForm, GroupManagerAssignmentForm
from groups.models import DelegatedGroup, GroupManagerAssignment
from groups.services.group_service import GroupService

logger = logging.getLogger(__name__)


class GroupListView(LoginRequiredMixin, View):
    """List all AD groups with search."""

    def get(self, request):
        service = GroupService()
        query = request.GET.get('q', '')
        page = int(request.GET.get('page', 1))
        try:
            if query:
                groups = service.search_groups(query)
                result = {
                    'groups': groups,
                    'total': len(groups),
                    'page': 1,
                    'has_next': False,
                    'has_prev': False,
                }
            else:
                result = service.list_groups(page=page)
            # Add encoded DNs for URL generation
            for g in result['groups']:
                g['encoded_dn'] = dn_to_base64(g['dn'])
                members = g['attributes'].get('member', [])
                if isinstance(members, str):
                    members = [members]
                g['member_count'] = len(members)
                group_type = g['attributes'].get('groupType', 0)
                if isinstance(group_type, list):
                    group_type = group_type[0] if group_type else 0
                try:
                    group_type = int(group_type)
                except (ValueError, TypeError):
                    group_type = 0
                if group_type & 0x80000000:
                    g['group_type_display'] = 'Security'
                else:
                    g['group_type_display'] = 'Distribution'
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to list groups: {exc}")
            result = {'groups': [], 'total': 0, 'page': 1,
                      'has_next': False, 'has_prev': False}
        return render(request, 'groups/group_list.html', {
            'result': result,
            'query': query,
        })


class GroupDetailView(LoginRequiredMixin, View):
    """Group detail with member list and management actions."""

    def get(self, request, encoded_dn):
        service = GroupService()
        dn = base64_to_dn(encoded_dn)
        try:
            group = service.get_group(dn)
            if not group:
                messages.error(request, "Group not found.")
                return redirect('groups:group_list')
            members = service.get_members(dn)
            can_manage = service.can_manage_group(request.user, dn)
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to load group: {exc}")
            return redirect('groups:group_list')
        return render(request, 'groups/group_detail.html', {
            'group': group,
            'members': members,
            'can_manage': can_manage,
            'encoded_dn': encoded_dn,
            'add_member_form': AddMemberForm(),
        })


class GroupAddMemberView(LoginRequiredMixin, View):
    """Add a member to a group (POST)."""

    def post(self, request, encoded_dn):
        service = GroupService()
        dn = base64_to_dn(encoded_dn)
        if not service.can_manage_group(request.user, dn):
            messages.error(request, "You do not have permission to manage this group.")
            return redirect('groups:group_detail', encoded_dn=encoded_dn)
        form = AddMemberForm(request.POST)
        if form.is_valid():
            member_dn = form.cleaned_data['member_dn']
            try:
                service.add_member(dn, member_dn)
                messages.success(request, "Member added successfully.")
            except LDAPServiceError as exc:
                messages.error(request, f"Failed to add member: {exc}")
        else:
            messages.error(request, "Invalid form data.")
        return redirect('groups:group_detail', encoded_dn=encoded_dn)


class GroupRemoveMemberView(LoginRequiredMixin, View):
    """Remove a member from a group (POST)."""

    def post(self, request, encoded_dn):
        service = GroupService()
        dn = base64_to_dn(encoded_dn)
        if not service.can_manage_group(request.user, dn):
            messages.error(request, "You do not have permission to manage this group.")
            return redirect('groups:group_detail', encoded_dn=encoded_dn)
        member_dn = request.POST.get('member_dn', '')
        if not member_dn:
            messages.error(request, "No member specified.")
            return redirect('groups:group_detail', encoded_dn=encoded_dn)
        try:
            service.remove_member(dn, member_dn)
            messages.success(request, "Member removed successfully.")
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to remove member: {exc}")
        return redirect('groups:group_detail', encoded_dn=encoded_dn)


class DelegationListView(RoleRequiredMixin, View):
    """Admin-only view to manage delegated groups."""

    required_roles = [ROLE_ADMIN]

    def get(self, request):
        delegated_groups = DelegatedGroup.objects.prefetch_related(
            'assignments__user'
        ).all()
        return render(request, 'groups/delegation_list.html', {
            'delegated_groups': delegated_groups,
        })


class DelegationCreateView(RoleRequiredMixin, View):
    """Admin-only view to create a delegated group."""

    required_roles = [ROLE_ADMIN]

    def get(self, request):
        form = DelegatedGroupForm()
        return render(request, 'groups/delegation_form.html', {'form': form})

    def post(self, request):
        form = DelegatedGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Delegated group created.")
            return redirect('groups:delegation_list')
        return render(request, 'groups/delegation_form.html', {'form': form})


class DelegationAssignView(RoleRequiredMixin, View):
    """Admin-only view to assign a manager to a delegated group."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, pk):
        delegated_group = get_object_or_404(DelegatedGroup, pk=pk)
        form = GroupManagerAssignmentForm()
        return render(request, 'groups/delegation_assign.html', {
            'form': form,
            'delegated_group': delegated_group,
        })

    def post(self, request, pk):
        delegated_group = get_object_or_404(DelegatedGroup, pk=pk)
        form = GroupManagerAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.delegated_group = delegated_group
            assignment.assigned_by = request.user
            assignment.save()
            messages.success(request, "Manager assigned successfully.")
            return redirect('groups:delegation_list')
        return render(request, 'groups/delegation_assign.html', {
            'form': form,
            'delegated_group': delegated_group,
        })


class MyGroupsView(RoleRequiredMixin, View):
    """GroupManager's view of their delegated groups."""

    required_roles = [ROLE_GROUP_MANAGER, ROLE_ADMIN, ROLE_HELPDESK]

    def get(self, request):
        assignments = GroupManagerAssignment.objects.filter(
            user=request.user,
            delegated_group__enabled=True,
        ).select_related('delegated_group')
        groups = []
        for assignment in assignments:
            groups.append({
                'delegated_group': assignment.delegated_group,
                'encoded_dn': dn_to_base64(assignment.delegated_group.group_dn),
            })
        return render(request, 'groups/my_groups.html', {'groups': groups})
