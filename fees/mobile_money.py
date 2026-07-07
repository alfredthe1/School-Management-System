"""Uganda mobile money — MTN MoMo and Airtel Money payment requests."""
import base64
import json
import uuid
from datetime import datetime

import requests
from django.conf import settings


class MobileMoneyAPIError(Exception):
    pass


def format_uganda_phone(phone):
    """Normalize to 2567XXXXXXXX format."""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '256' + phone[1:]
    elif not phone.startswith('256'):
        phone = '256' + phone
    return phone


class UgandaMobileMoneyClient:
    """Request-to-pay client for MTN Mobile Money and Airtel Money (Uganda)."""

    PROVIDER_MTN = 'mtn'
    PROVIDER_AIRTEL = 'airtel'

    def __init__(self, provider=PROVIDER_MTN):
        if provider not in (self.PROVIDER_MTN, self.PROVIDER_AIRTEL):
            raise ValueError(f'Unsupported provider: {provider}')
        self.provider = provider

    def is_configured(self):
        if self.provider == self.PROVIDER_MTN:
            return all([
                getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', ''),
                getattr(settings, 'MTN_MOMO_API_USER', ''),
                getattr(settings, 'MTN_MOMO_API_KEY', ''),
                getattr(settings, 'MTN_MOMO_CALLBACK_URL', ''),
            ])
        return all([
            getattr(settings, 'AIRTEL_MONEY_CLIENT_ID', ''),
            getattr(settings, 'AIRTEL_MONEY_CLIENT_SECRET', ''),
            getattr(settings, 'AIRTEL_MONEY_CALLBACK_URL', ''),
        ])

    @property
    def provider_label(self):
        return 'MTN Mobile Money' if self.provider == self.PROVIDER_MTN else 'Airtel Money'

    def request_payment(self, phone, amount, account_reference, description):
        phone = format_uganda_phone(phone)
        if not self.is_configured():
            return self._simulate_request(phone, amount, account_reference)

        if self.provider == self.PROVIDER_MTN:
            return self._mtn_request_to_pay(phone, amount, account_reference, description)
        return self._airtel_collect(phone, amount, account_reference, description)

    def _simulate_request(self, phone, amount, reference):
        ref_id = f'SIM-{uuid.uuid4().hex[:12].upper()}'
        return {
            'reference_id': ref_id,
            'external_id': ref_id,
            'status': 'PENDING',
            'simulated': True,
            'message': f'Simulated {self.provider_label} prompt sent to {phone}',
        }

    def _mtn_get_token(self):
        url = getattr(
            settings, 'MTN_MOMO_TOKEN_URL',
            'https://sandbox.momodeveloper.mtn.com/collection/token/',
        )
        user_id = settings.MTN_MOMO_API_USER
        api_key = settings.MTN_MOMO_API_KEY
        auth = base64.b64encode(f'{user_id}:{api_key}'.encode()).decode()
        response = requests.post(
            url,
            headers={
                'Authorization': f'Basic {auth}',
                'Ocp-Apim-Subscription-Key': settings.MTN_MOMO_SUBSCRIPTION_KEY,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()['access_token']

    def _mtn_request_to_pay(self, phone, amount, reference, description):
        ref_id = str(uuid.uuid4())
        url = getattr(
            settings, 'MTN_MOMO_REQUEST_URL',
            'https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay',
        )
        token = self._mtn_get_token()
        payload = {
            'amount': str(int(amount)),
            'currency': getattr(settings, 'MTN_MOMO_CURRENCY', 'UGX'),
            'externalId': reference[:36],
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': phone,
            },
            'payerMessage': description[:160],
            'payeeNote': f'School fees {reference}'[:160],
        }
        response = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'X-Reference-Id': ref_id,
                'X-Target-Environment': getattr(settings, 'MTN_MOMO_ENV', 'sandbox'),
                'Ocp-Apim-Subscription-Key': settings.MTN_MOMO_SUBSCRIPTION_KEY,
                'Content-Type': 'application/json',
                'X-Callback-Url': settings.MTN_MOMO_CALLBACK_URL,
            },
            timeout=30,
        )
        if response.status_code not in (200, 202):
            raise MobileMoneyAPIError(
                response.text or f'MTN request failed ({response.status_code})'
            )
        return {
            'reference_id': ref_id,
            'external_id': reference,
            'status': 'PENDING',
            'simulated': False,
            'message': 'Payment prompt sent to your MTN Mobile Money number.',
        }

    def _airtel_get_token(self):
        url = getattr(
            settings, 'AIRTEL_MONEY_TOKEN_URL',
            'https://openapiuat.airtel.africa/auth/oauth2/token',
        )
        response = requests.post(
            url,
            json={
                'client_id': settings.AIRTEL_MONEY_CLIENT_ID,
                'client_secret': settings.AIRTEL_MONEY_CLIENT_SECRET,
                'grant_type': 'client_credentials',
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()['access_token']

    def _airtel_collect(self, phone, amount, reference, description):
        ref_id = str(uuid.uuid4())
        url = getattr(
            settings, 'AIRTEL_MONEY_COLLECT_URL',
            'https://openapiuat.airtel.africa/merchant/v1/payments/',
        )
        token = self._airtel_get_token()
        payload = {
            'reference': ref_id,
            'subscriber': {
                'country': 'UG',
                'currency': getattr(settings, 'AIRTEL_MONEY_CURRENCY', 'UGX'),
                'msisdn': phone,
            },
            'transaction': {
                'amount': int(amount),
                'country': 'UG',
                'currency': getattr(settings, 'AIRTEL_MONEY_CURRENCY', 'UGX'),
                'id': ref_id,
            },
        }
        response = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'X-Country': 'UG',
                'X-Currency': getattr(settings, 'AIRTEL_MONEY_CURRENCY', 'UGX'),
            },
            timeout=30,
        )
        data = response.json() if response.content else {}
        if response.status_code not in (200, 201):
            raise MobileMoneyAPIError(
                data.get('message') or data.get('status_message') or response.text
            )
        return {
            'reference_id': ref_id,
            'external_id': reference,
            'status': 'PENDING',
            'simulated': False,
            'message': 'Payment prompt sent to your Airtel Money number.',
        }


def parse_mtn_callback(payload):
    """Parse MTN MoMo collection callback."""
    ref = payload.get('referenceId') or payload.get('externalId', '')
    status = (payload.get('status') or '').upper()
    success = status in ('SUCCESSFUL', 'SUCCESS')
    return {
        'success': success,
        'reference_id': ref,
        'transaction_reference': payload.get('financialTransactionId', ref),
        'result_desc': payload.get('reason') or status or 'MTN callback received',
        'amount': payload.get('amount'),
    }


def parse_airtel_callback(payload):
    """Parse Airtel Money payment callback."""
    transaction = payload.get('transaction', {})
    status = (transaction.get('status') or payload.get('status', '')).upper()
    success = status in ('SUCCESS', 'TS', 'SUCCESSFUL')
    ref = transaction.get('id') or payload.get('reference', '')
    return {
        'success': success,
        'reference_id': ref,
        'transaction_reference': transaction.get('airtel_money_id', ref),
        'result_desc': payload.get('message') or status or 'Airtel callback received',
        'amount': transaction.get('amount'),
    }