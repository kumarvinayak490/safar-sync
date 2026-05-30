import json

import pytest


class FakeRazorpayOrderResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeRazorpayOrderClient:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout=None):
        if not request.full_url.rstrip("/").endswith("/orders"):
            raise AssertionError(f"Unexpected Razorpay HTTP call to {request.full_url}")
        payload = json.loads(request.data.decode("utf-8"))
        headers = dict(request.header_items())
        self.requests.append(
            {
                "url": request.full_url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return FakeRazorpayOrderResponse(
            {
                "id": f"order_{payload['receipt']}",
                "entity": "order",
                "amount": payload["amount"],
                "amount_paid": 0,
                "amount_due": payload["amount"],
                "currency": payload["currency"],
                "receipt": payload["receipt"],
                "status": "created",
                "attempts": 0,
                "notes": payload.get("notes", {}),
            }
        )


@pytest.fixture(autouse=True)
def fake_razorpay_order_creation(monkeypatch):
    client = FakeRazorpayOrderClient()
    monkeypatch.setattr("trip_payments.provider_adapters.urlopen", client)
    return client
