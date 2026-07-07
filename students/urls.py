from django.urls import path
from . import views

app_name = 'students'
urlpatterns = [
    path('', views.StudentListView.as_view(), name='list'),
    path('add/', views.StudentCreateView.as_view(), name='add'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/results/', views.student_results, name='results'),
    path('<int:pk>/results/edit/', views.student_results_edit, name='results_edit'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.StudentDeleteView.as_view(), name='delete'),
    path('export/pdf/', views.StudentPDFView.as_view(), name='export_pdf'),  # new
]