from django.contrib import admin
from django.urls import include, path

from apps.core.views import health_check
from apps.organizations.views import accept_invitation_view
from apps.teams.views import team_list_view

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("invitations/<str:token>/", accept_invitation_view, name="accept_invitation"),
    path("organizations/<slug:slug>/team/", team_list_view, name="organization_teams"),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
]
