from django.urls import path
from . import views

app_name = 'parents'
urlpatterns = [
    path('dashboard/', views.parent_dashboard, name='dashboard'),
    path('children/', views.my_children, name='my_children'),
    path('child/<int:student_id>/', views.child_progress, name='child_progress'),
    path('link-child/', views.link_child, name='link_child'),
    path('pay-fees/', views.pay_fees_hub, name='pay_fees_hub'),
    path('pay/<int:student_id>/', views.pay_fees, name='pay_fees'),
    path('payment/<int:transaction_id>/', views.payment_status, name='payment_status'),
    path('payment/<int:transaction_id>/poll/', views.payment_status_poll, name='payment_status_poll'),
    path('payments/history/', views.payment_history, name='payment_history'),
    path('payments/record/<int:payment_id>/', views.payment_record_detail, name='payment_record_detail'),
    path('mobile-money/mtn/callback/', views.mtn_callback, name='mtn_callback'),
    path('mobile-money/airtel/callback/', views.airtel_callback, name='airtel_callback'),
]