from django.urls import path
from . import views
app_name = "publishers"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organization/new/", views.create_organization, name="create_organization"),
    path("organization/<int:organization_id>/release/new/", views.submit_release, name="submit_release"),
]
