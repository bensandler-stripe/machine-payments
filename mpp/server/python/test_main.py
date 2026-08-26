import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mpp import Receipt


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_PROFILE_ID", "profile_test_123")
    monkeypatch.setenv("TEMPO_DEPOSIT_ADDRESS", "0x" + "1" * 40)


def test_app_is_fastapi():
    from main import app

    assert isinstance(app, FastAPI)


@pytest.mark.asyncio
async def test_post_paid_returns_402_without_payment():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/paid")

    assert response.status_code == 402


@pytest.mark.asyncio
async def test_openapi_describes_the_canonical_paid_endpoint():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/paid"]["post"]
    assert operation["requestBody"]["required"] is False
    assert {"200", "402"}.issubset(operation["responses"])
    offers = operation["x-payment-info"]["offers"]
    assert [offer["method"] for offer in offers] == ["tempo", "stripe"]
    offers_by_method = {offer["method"]: offer for offer in offers}
    assert offers_by_method["tempo"]["amount"] == "500000"
    assert offers_by_method["stripe"]["amount"] == "50"


def test_paid_response_includes_the_payment_receipt():
    from main import paid_response

    receipt = Receipt.success("0xpaid", method="tempo")
    response = paid_response(receipt)

    assert response.headers["payment-receipt"] == receipt.to_payment_receipt()
