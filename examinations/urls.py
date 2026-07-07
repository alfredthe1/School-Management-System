from django.urls import path
from . import views

app_name = 'examinations'
urlpatterns = [
    # Teacher routes
    path('teacher/marks/', views.teacher_marks_hub, name='teacher_marks_hub'),
    path('teacher/exams/', views.teacher_exam_list, name='teacher_exam_list'),
    path('teacher/enter/<int:exam_id>/', views.teacher_enter_marks, name='teacher_enter_marks'),
    path('teacher/view/', views.teacher_view_results, name='teacher_view_results'),
    path('teacher/result/<int:exam_id>/', views.teacher_result_detail, name='teacher_result_detail'),

    # Admin/Headteacher routes
    path('admin/list/', views.ExamListView.as_view(), name='exam_list'),
    path('admin/add/', views.ExamCreateView.as_view(), name='exam_add'),
    path('admin/<int:pk>/edit/', views.ExamUpdateView.as_view(), name='exam_edit'),
    path('admin/<int:pk>/delete/', views.ExamDeleteView.as_view(), name='exam_delete'),
    path('admin/<int:exam_id>/results/', views.exam_results, name='exam_results'),
    path('admin/<int:exam_id>/enter/', views.teacher_enter_marks, name='admin_enter_marks'),
    path('admin/grade-scales/', views.grade_scale_list, name='grade_scales'),
    path('admin/grade-scales/<int:pk>/delete/', views.grade_scale_delete, name='grade_scale_delete'),

    # Shared results view
    path('view-results/', views.teacher_view_results, name='exam_results_list'),
]