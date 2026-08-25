# frozen_string_literal: true

require "json"
require "minitest/autorun"
require "rack/mock"

ENV["STRIPE_SECRET_KEY"] = "sk_test_fake"
ENV["STRIPE_PROFILE_ID"] = "profile_test_123"
ENV["TEMPO_DEPOSIT_ADDRESS"] = "0x#{"1" * 40}"

require_relative "../app"

class AppTest < Minitest::Test
  def app
    App.new
  end

  def test_openapi_describes_the_canonical_paid_endpoint
    response = Rack::MockRequest.new(app).get("/openapi.json")

    assert_equal 200, response.status
    document = JSON.parse(response.body)
    operation = document.fetch("paths").fetch("/paid").fetch("post")

    assert_equal "3.1.0", document.fetch("openapi")
    assert_equal "MPP REST API", document.fetch("info").fetch("title")
    assert_equal false, operation.fetch("requestBody").fetch("required")
    assert operation.fetch("responses").key?("402")
    offers = operation.fetch("x-payment-info").fetch("offers")
    assert_equal ["tempo", "stripe"], offers.map { |offer| offer.fetch("method") }
    offers_by_method = offers.to_h { |offer| [offer.fetch("method"), offer] }
    assert_equal "500000", offers_by_method.fetch("tempo").fetch("amount")
    assert_equal "50", offers_by_method.fetch("stripe").fetch("amount")
  end

  def test_paid_returns_a_payment_challenge_without_credentials
    response = Rack::MockRequest.new(app).post("/paid")

    assert_equal 402, response.status
    assert Array(response["WWW-Authenticate"]).all? { |value| value.start_with?("Payment ") }
  end
end
