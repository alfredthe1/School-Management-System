from django.urls import path
from . import views, import_views, structure_views

app_name = 'core'
urlpatterns = [
    path('', views.home, name='home'),  # Landing page
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('landing-images/', views.landing_images_upload, name='landing_images_upload'),
    path('landing-images/delete/<int:pk>/', views.delete_landing_image, name='delete_landing_image'),
    path('teacher/lesson-plans/', views.teacher_lesson_plans, name='teacher_lesson_plans'),
    path('import/', import_views.import_hub, name='import_hub'),
    path('import/template/<str:import_type>/', import_views.download_import_template, name='import_template'),
    # School structure — classes, streams, subjects
    path('classes/', structure_views.class_list, name='class_list'),
    path('classes/add/', structure_views.class_create, name='class_create'),
    path('classes/<int:pk>/', structure_views.class_detail, name='class_detail'),
    path('classes/<int:pk>/edit/', structure_views.class_edit, name='class_edit'),
    path('classes/<int:pk>/delete/', structure_views.class_delete, name='class_delete'),
    path('subjects/', structure_views.subject_list, name='subject_list'),
    path('subjects/add/', structure_views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/edit/', structure_views.subject_edit, name='subject_edit'),
    path('subjects/<int:pk>/delete/', structure_views.subject_delete, name='subject_delete'),
    path('subjects/assignments/', structure_views.subject_assignments, name='subject_assignments'),
]