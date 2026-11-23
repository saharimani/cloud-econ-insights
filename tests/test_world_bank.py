"""Tests for the World Bank integration, with the HTTP call replaced by a stub.

Run: python -m unittest discover -s tests -v
"""
import unittest
from unittest import mock

import external_api
from app import create_app
from models import EconSnapshot, db


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "testing-only"


def fake_response(payload, status=200):
    response = mock.Mock()
    response.ok = status == 200
    response.status_code = status
    response.json.return_value = payload
    return response


class WorldBankClientTests(unittest.TestCase):
    """The client parses the World Bank's [metadata, records] response shape."""

    @mock.patch("external_api.requests.get")
    def test_returns_the_value(self, get):
        get.return_value = fake_response([{"page": 1}, [{"value": 2.36}]])
        self.assertEqual(external_api.fetch_indicator_value("GB", "NY.GDP.MKTP.KD.ZG", 2022), 2.36)
        url = get.call_args.args[0]
        self.assertTrue(url.endswith("/country/GB/indicator/NY.GDP.MKTP.KD.ZG"))

    @mock.patch("external_api.requests.get")
    def test_missing_or_bad_data_returns_none(self, get):
        for payload, status in [([{"page": 1}, []], 200),
                                ([{"message": "Invalid value"}], 200),
                                (None, 500)]:
            get.return_value = fake_response(payload, status)
            self.assertIsNone(external_api.fetch_indicator_value("GB", "X", 2022))

    @mock.patch("external_api.requests.get",
                side_effect=external_api.requests.exceptions.Timeout)
    def test_timeout_returns_none(self, _):
        self.assertIsNone(external_api.fetch_indicator_value("GB", "X", 2022))


class FetchSnapshotRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def register(self, name):
        response = self.client.post("/auth/register", json={
            "email": f"{name}@example.com", "password": "test-pass-123"})
        return {"X-API-KEY": response.json["api_key"]}

    def indicator(self, headers, code="NY.GDP.MKTP.KD.ZG"):
        response = self.client.post("/indicators/", headers=headers,
                                    json={"code": code, "name": "GDP growth"})
        return response.json["id"]

    @mock.patch("external_api.fetch_indicator_value", return_value=2.36)
    def test_fetch_stores_the_live_value(self, fetch):
        alice = self.register("alice")
        indicator_id = self.indicator(alice)

        response = self.client.post("/snapshots/fetch", headers=alice, json={
            "indicator_id": indicator_id, "country": "gb", "year": 2022})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["value"], 2.36)
        self.assertEqual(response.json["country"], "GB")
        fetch.assert_called_once_with("GB", "NY.GDP.MKTP.KD.ZG", 2022)
        self.assertEqual(EconSnapshot.query.count(), 1)

    @mock.patch("external_api.fetch_indicator_value", return_value=None)
    def test_no_value_is_a_bad_gateway_and_stores_nothing(self, _):
        alice = self.register("alice")
        response = self.client.post("/snapshots/fetch", headers=alice, json={
            "indicator_id": self.indicator(alice), "country": "GB", "year": 1800})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(EconSnapshot.query.count(), 0)

    @mock.patch("external_api.fetch_indicator_value")
    def test_cannot_fetch_with_another_users_indicator(self, fetch):
        alice = self.register("alice")
        bob = self.register("bob")
        response = self.client.post("/snapshots/fetch", headers=bob, json={
            "indicator_id": self.indicator(alice), "country": "GB", "year": 2022})
        self.assertEqual(response.status_code, 404)
        fetch.assert_not_called()

    @mock.patch("external_api.fetch_indicator_value")
    def test_input_is_validated_before_calling_the_api(self, fetch):
        alice = self.register("alice")
        good = self.indicator(alice)
        unsafe = self.indicator(alice, code="../../admin")
        for body in [{"indicator_id": good, "country": "G1", "year": 2022},
                     {"indicator_id": good, "country": "GB", "year": "soon"},
                     {"indicator_id": unsafe, "country": "GB", "year": 2022}]:
            self.assertEqual(self.client.post("/snapshots/fetch", headers=alice,
                                              json=body).status_code, 400)
        self.assertEqual(self.client.post("/snapshots/fetch", json={}).status_code, 401)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
