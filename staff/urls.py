from django.urls import path

from . import views

app_name = 'staff'
urlpatterns = [
    path('', views.StaffListView.as_view(), name='list'),
    path('add/', views.StaffCreateView.as_view(), name='add'),
    path('<int:pk>/', views.StaffDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.StaffUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.StaffDeleteView.as_view(), name='delete'),

    path('<int:pk>/allowances/', views.manage_allowances, name='allowances'),
    path('<int:pk>/allowances/<int:allowance_id>/toggle/', views.toggle_allowance, name='toggle_allowance'),
    path('<int:pk>/allowances/<int:allowance_id>/delete/', views.delete_allowance, name='delete_allowance'),

    path('payroll/', views.payroll_dashboard, name='payroll_dashboard'),
    path('payroll/generate/', views.generate_payroll_view, name='generate_payroll'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/item/<int:pk>/edit/', views.edit_payroll_item, name='edit_payroll_item'),
    path('payroll/<int:pk>/mark-paid/', views.mark_payroll_paid, name='mark_payroll_paid'),
    path('<int:staff_pk>/pay/', views.record_salary_payment, name='record_payment'),

    path('my-payroll/', views.my_payroll, name='my_payroll'),
]