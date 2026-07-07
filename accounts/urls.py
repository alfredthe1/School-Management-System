from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, user_views

app_name = 'accounts'
urlpatterns = [
    path('users/', user_views.user_list, name='user_list'),
    path('users/add/', user_views.user_create, name='user_create'),
    path('users/<int:pk>/', user_views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', user_views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', user_views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/reset-password/', user_views.user_reset_password, name='user_reset_password'),
    path('users/<int:pk>/permissions/', user_views.user_permissions, name='user_permissions'),
    path('login/', views.RoleBasedLoginView.as_view(), name='login'),
    path('signup/', views.parent_signup, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/change_password.html',
        success_url='/accounts/profile/',
    ), name='change_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]