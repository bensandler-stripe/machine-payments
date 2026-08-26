import hashlib
import hmac
import os
from decimal import Decimal
from typing import Any

import stripe as stripe_sdk
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mpp import Credential, Receipt
from mpp.methods import stripe
from mpp.server import Mpp  # pyright: ignore[reportPrivateImportUsage]

load_dotenv()

# Don't put any keys in code. Use an environment variable (as shown
# here) or secrets vault to supply keys to your integration.
#
# See https://docs.stripe.com/keys-best-practices and find your
# keys at https://dashboard.stripe.com/apikeys.
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET_KEY:
    raise ValueError("STRIPE_SECRET_KEY environment variable is required")

TEMPO_DEPOSIT_ADDRESS = os.getenv("TEMPO_DEPOSIT_ADDRESS")
if not TEMPO_DEPOSIT_ADDRESS:
    raise ValueError(
        "TEMPO_DEPOSIT_ADDRESS environment variable is required.\n"
        "Create one with: stripe post /v1/crypto/deposit_addresses "
        "--live --stripe-version 2026-05-27.preview -d network=tempo"
    )

STRIPE_PROFILE_ID = os.getenv("STRIPE_PROFILE_ID")
if not STRIPE_PROFILE_ID:
    raise ValueError("STRIPE_PROFILE_ID environment variable is required")

stripe_sdk.set_app_info(
    "stripe-samples/machine-payments",
    url="https://github.com/stripe-samples/machine-payments",
    version="1.0.0",
)

# Secret used to secure payment challenges.
# https://mpp.dev/protocol/challenges#challenge-binding
mpp_secret_key = hmac.new(
    STRIPE_SECRET_KEY.encode(),
    b"mpp-challenge-signing",
    hashlib.sha256,
).hexdigest()

PRICE_USD = "0.50"
DESCRIPTION = "Returns paid content"
PORT = int(os.getenv("PORT", "4242"))

stripe_client = stripe_sdk.StripeClient(STRIPE_SECRET_KEY)
payments = stripe.create(
    network_id=STRIPE_PROFILE_ID,
    livemode="_test_" not in STRIPE_SECRET_KEY,
    client=stripe_client,
    deposit_addresses={"tempo": TEMPO_DEPOSIT_ADDRESS},
)
payment_methods = payments.default_methods()
server = Mpp.create(
    methods=payment_methods,
    secret_key=mpp_secret_key,
)

app = FastAPI(title="MPP REST API")


def payment_offer(method: Any) -> dict[str, str]:
    """Describe a fixed-price charge offer for OpenAPI payment discovery."""
    decimals = method.decimals
    amount = int(Decimal(PRICE_USD) * 10**decimals)
    return {
        "amount": str(amount),
        "currency": method.currency,
        "description": DESCRIPTION,
        "intent": "charge",
        "method": method.name,
        "recipient": method.recipient,
    }


def paid_response(receipt: Receipt) -> JSONResponse:
    response = JSONResponse(content={"foo": "bar"})
    response.headers["Payment-Receipt"] = receipt.to_payment_receipt()
    return response


@app.post(
    "/paid",
    summary=DESCRIPTION,
    responses={402: {"description": "Payment Required"}},
    openapi_extra={
        "requestBody": {
            "description": "Optional JSON request data.",
            "required": False,
            "content": {"application/json": {"schema": {"type": "object"}}},
        },
        "x-payment-info": {
            "offers": [payment_offer(method) for method in payment_methods]
        },
    },
)
@server.pay(
    amount=PRICE_USD,
    description=DESCRIPTION,
    body=lambda request: request.body(),
)
async def post_paid(
    request: Request, credential: Credential, receipt: Receipt
) -> JSONResponse:
    return paid_response(receipt)


if __name__ == "__main__":
    print(f"Server listening at http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
