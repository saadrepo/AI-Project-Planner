from django.urls import path

from .views import (
    accept_invitation_view,
    create_invitation_view,
    member_remove_view,
    member_role_view,
    organization_create_view,
    organization_detail_view,
    organization_list_view,
    organization_members_view,
    organization_member_assign_view,
    organization_settings_view,
    organization_switch_view,
    resend_invitation_view,
    revoke_invitation_view,
    organization_invitations_view,
)

urlpatterns = [
    path("", organization_list_view, name="organization_list"),
    path("create/", organization_create_view, name="organization_create"),
    path("switch/", organization_switch_view, name="organization_switch"),
    path("<slug>/", organization_detail_view, name="organization_detail"),
    path("<slug>/settings/", organization_settings_view, name="organization_settings"),
    path("<slug>/members/", organization_members_view, name="organization_members"),
    path("<slug>/members/assign/", organization_member_assign_view, name="organization_member_assign"),
    path("<slug>/members/<uuid:member_id>/role/", member_role_view, name="member_role"),
    path("<slug>/members/<uuid:member_id>/remove/", member_remove_view, name="member_remove"),
    path("<slug>/invitations/", organization_invitations_view, name="organization_invitations"),
    path("<slug>/invitations/create/", create_invitation_view, name="create_invitation"),
    path("<slug>/invitations/<uuid:invitation_id>/resend/", resend_invitation_view, name="resend_invitation"),
    path("<slug>/invitations/<uuid:invitation_id>/revoke/", revoke_invitation_view, name="revoke_invitation"),
]
