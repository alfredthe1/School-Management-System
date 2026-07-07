from django.urls import path
from . import views

app_name = 'fees'
urlpatterns = [
    path('', views.fee_dashboard, name='fee_dashboard'),

    # Fee Structures
    path('structures/', views.fee_structure_list, name='fee_structure_list'),
    path('structures/add/', views.fee_structure_add, name='fee_structure_add'),
    path('structures/edit/<int:pk>/', views.fee_structure_edit, name='fee_structure_edit'),
    path('structures/delete/<int:pk>/', views.fee_structure_delete, name='fee_structure_delete'),

    # Expenditures
    path('expenditures/', views.expenditure_list, name='expenditure_list'),
    path('expenditures/add/', views.expenditure_add, name='expenditure_add'),
    path('expenditures/edit/<int:pk>/', views.expenditure_edit, name='expenditure_edit'),
    path('expenditures/delete/<int:pk>/', views.expenditure_delete, name='expenditure_delete'),

    # Payments (global list)
    path('payments/', views.payment_list, name='payment_list'),
    path('payment/record/', views.record_payment, name='record_payment'),

    # Student-level payments
    path('student/<int:student_id>/', views.student_fees, name='student_fees'),
    path('payment/add/<int:student_id>/', views.add_payment, name='add_payment'),
    path('payment/edit/<int:payment_id>/', views.edit_payment, name='edit_payment'),
    path('payment/delete/<int:payment_id>/', views.delete_payment, name='delete_payment'),

    path('payments/pdf/', views.PaymentPDFView.as_view(), name='payment_pdf'),
    path('expenditures/pdf/', views.ExpenditurePDFView.as_view(), name='expenditure_pdf'),

    # Reports
    path('reports/collection/', views.collection_report, name='collection_report'),
    path('payment-gateway/', views.payment_gateway_settings, name='payment_gateway'),
    path('parent-result-access/', views.parent_result_access, name='parent_result_access'),
]