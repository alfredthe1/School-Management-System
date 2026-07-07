from django.urls import path
from . import views

app_name = 'communication'
urlpatterns = [
    path('send-sms/', views.send_bulk_sms, name='send_sms'),
    path('bulk/', views.send_bulk_communication, name='bulk_communication'),
    path('inbox/', views.message_inbox, name='inbox'),
    path('notification/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('send-message/', views.send_internal_message, name='send_message'),
]