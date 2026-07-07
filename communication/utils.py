from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
from django.conf import settings

def send_sms(phone_number, message):
    if settings.TWILIO_ACCOUNT_SID:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
    else:
        # Placeholder: print to console
        print(f"[SMS] To {phone_number}: {message}")

def send_email_notification(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )