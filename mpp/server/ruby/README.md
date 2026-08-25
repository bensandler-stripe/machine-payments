# MPP REST API - Ruby

This Ruby implementation of the MPP REST API accepts Tempo and Stripe shared
payment token (SPT) payments. Successful Tempo payments are automatically
recorded as Stripe crypto PaymentIntents.

## Requirements

- Ruby 3.3+
- Bundler and `make`
- A Stripe account with crypto payments enabled
- A static Tempo Stripe deposit address

## Setup

1. Create a Tempo crypto deposit address:

```bash
stripe post /v1/crypto/deposit_addresses --live --stripe-version 2026-05-27.preview -d network=tempo
```

2. Configure the required environment variables:

```bash
cp ../../../.env.template .env
# Edit .env with:
# - STRIPE_SECRET_KEY
# - STRIPE_PROFILE_ID
# - TEMPO_DEPOSIT_ADDRESS
```

3. Install dependencies:

```bash
make install
```

For development against an unmerged local `mpp-rb` checkout, point Bundler at
it without changing this sample's Gemfile:

```bash
export MPP_RB_PATH=../../../../mpp-rb-stripe-machine-payments
make install
```

## Run the server

```bash
make run
```

The server listens on `http://localhost:4242`.

## Validate the implementation

```bash
npx mppx@latest validate http://localhost:4242
```

The OpenAPI 3.1 discovery document is at:

```bash
curl http://localhost:4242/openapi.json
```

## Development commands

- `make lint` — run formatting and lint checks
- `make format` — apply formatting fixes
- `make typecheck` — check Ruby syntax
- `make test` — run automated tests
- `make ci` — install and run the local checks
