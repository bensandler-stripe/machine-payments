# frozen_string_literal: true

require "base64"
require "json"
require "openssl"

require "dotenv/load"
require "mpp-rb"
require "sinatra/base"
require "stripe"

module MachinePaymentsSample
  AMOUNT_USD = "0.50"
  DESCRIPTION = "Returns paid content"

  module_function

  def required_env(name)
    value = ENV[name]
    return value unless value.nil? || value.empty?

    abort "#{name} environment variable is required"
  end

  def payment_secret(secret_key)
    digest = OpenSSL::HMAC.digest("SHA256", secret_key, "mpp-challenge-signing")
    Base64.strict_encode64(digest)
  end

  def livemode?(secret_key)
    !secret_key.include?("_test_")
  end

  def payment_offer(server, method)
    request = server.build_charge_request(method, AMOUNT_USD)
    {
      "amount" => request.fetch("amount"),
      "currency" => request.fetch("currency"),
      "description" => DESCRIPTION,
      "intent" => "charge",
      "method" => method.name,
      "recipient" => request.fetch("recipient")
    }
  end
end

stripe_secret_key = MachinePaymentsSample.required_env("STRIPE_SECRET_KEY")
stripe_profile_id = MachinePaymentsSample.required_env("STRIPE_PROFILE_ID")
tempo_deposit_address = MachinePaymentsSample.required_env("TEMPO_DEPOSIT_ADDRESS")

Stripe.set_app_info(
  "stripe-samples/machine-payments",
  version: "1.0.0",
  url: "https://github.com/stripe-samples/machine-payments"
)
stripe_client = Stripe::StripeClient.new(stripe_secret_key)
machine_payments = Mpp::Methods::Stripe.create(
  client: stripe_client,
  network_id: stripe_profile_id,
  livemode: MachinePaymentsSample.livemode?(stripe_secret_key),
  deposit_addresses: {tempo: tempo_deposit_address}
)
payment_methods = machine_payments.default_methods

payment_server = Mpp.create(
  methods: payment_methods,
  realm: "localhost",
  secret_key: MachinePaymentsSample.payment_secret(stripe_secret_key)
)

paid = payment_server.compose(*payment_methods.map do |method|
  [method, {amount: MachinePaymentsSample::AMOUNT_USD, description: MachinePaymentsSample::DESCRIPTION}]
end)

openapi_document = {
  "openapi" => "3.1.0",
  "info" => {"title" => "MPP REST API", "version" => "1.0.0"},
  "paths" => {
    "/paid" => {
      "post" => {
        "summary" => MachinePaymentsSample::DESCRIPTION,
        "requestBody" => {
          "description" => "Optional JSON request data.",
          "required" => false,
          "content" => {"application/json" => {"schema" => {"type" => "object"}}}
        },
        "x-payment-info" => {
          "offers" => payment_methods.map do |method|
            MachinePaymentsSample.payment_offer(payment_server, method)
          end
        },
        "responses" => {
          "200" => {"description" => "Successful response"},
          "402" => {"description" => "Payment Required"}
        }
      }
    }
  }
}.freeze

class App < Sinatra::Base
  set :bind, "0.0.0.0"
  set :port, 4242

  get "/openapi.json" do
    content_type :json
    JSON.generate(settings.openapi_document)
  end

  post "/paid" do
    body = request.body&.read.to_s
    result = settings.paid.call(
      authorization: env["HTTP_AUTHORIZATION"],
      accept_payment: env["HTTP_ACCEPT_PAYMENT"],
      body: body.empty? ? nil : body,
      url: request.url,
      http_method: request.request_method
    )

    if result.payment_required?
      response = result.to_response
      halt [response.fetch("status"), response.fetch("headers"), [response.fetch("body")]]
    end

    _credential, receipt = result.payment
    headers "Payment-Receipt" => receipt.to_payment_receipt
    result.extra_headers.each { |key, value| headers key => value unless value.nil? }
    content_type :json
    JSON.generate({foo: "bar"})
  end
end

App.set :openapi_document, openapi_document
App.set :paid, paid

App.run! if $PROGRAM_NAME == __FILE__
