from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
app_name = "accounts"
urlpatterns = [
    path("register/", views.register, name="register"),
    path("home/", views.account_home, name="home"),
    path("recover/", views.reset_with_recovery_code, name="recover"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
