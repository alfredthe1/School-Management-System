from django.urls import path
from . import views

app_name = 'reports'
urlpatterns = [
    path('excel/', views.generate_class_report_excel, name='excel_report'),
    path('report-card/<int:student_id>/', views.student_report_card, name='student_report_card'),
    path('fee-balance/<int:student_id>/', views.fee_balance_statement, name='fee_balance'),
    path('custom/', views.custom_report_builder, name='custom_report'),
]