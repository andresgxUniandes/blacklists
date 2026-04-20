import uuid

VALID_UUID = str(uuid.uuid4())
VALID_EMAIL = "test@example.com"


class TestBlacklistGet:
    def test_requires_auth(self, client):
        response = client.get(f"/blacklists?email={VALID_EMAIL}")

        assert response.status_code == 401

    def test_missing_email_param_returns_400(self, client, auth_header):
        response = client.get("/blacklists", headers=auth_header)

        assert response.status_code == 400
        assert "mensaje" in response.get_json()

    def test_invalid_email_format_returns_400(self, client, auth_header):
        response = client.get("/blacklists?email=notanemail", headers=auth_header)

        assert response.status_code == 400
        assert "mensaje" in response.get_json()

    def test_email_not_in_blacklist_returns_404(self, client, auth_header):
        response = client.get(
            "/blacklists?email=unknown@example.com",
            headers=auth_header,
        )

        assert response.status_code == 404
        body = response.get_json()
        assert body["is_blacklisted"] is False
        assert body["email"] == "unknown@example.com"

    def test_email_in_blacklist_returns_200(self, client, auth_header, existing_entry):
        response = client.get(
            "/blacklists?email=blocked@example.com",
            headers=auth_header,
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["is_blacklisted"] is True
        assert body["email"] == "blocked@example.com"
        assert body["reason"] == "Test reason"

    def test_query_is_case_insensitive(self, client, auth_header, existing_entry):
        response = client.get(
            "/blacklists?email=BLOCKED@EXAMPLE.COM",
            headers=auth_header,
        )

        assert response.status_code == 200
        assert response.get_json()["is_blacklisted"] is True

    def test_path_based_lookup_found(self, client, auth_header, existing_entry):
        response = client.get(
            "/blacklists/blocked%40example.com",
            headers=auth_header,
        )

        assert response.status_code == 200
        assert response.get_json()["is_blacklisted"] is True

    def test_path_based_lookup_not_found(self, client, auth_header):
        response = client.get(
            "/blacklists/nobody%40example.com",
            headers=auth_header,
        )

        assert response.status_code == 404
        assert response.get_json()["is_blacklisted"] is False


class TestBlacklistPost:
    def test_requires_auth(self, client):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
        )

        assert response.status_code == 401

    def test_create_entry_returns_201(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 201
        body = response.get_json()
        assert body["email"] == VALID_EMAIL
        assert body["app_uuid"] == VALID_UUID

    def test_response_includes_all_expected_fields(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 201
        body = response.get_json()
        assert "id" in body
        assert "email" in body
        assert "app_uuid" in body
        assert "ip_address" in body
        assert "created_at" in body

    def test_create_with_blocked_reason(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID, "blocked_reason": "Spam"},
            headers=auth_header,
        )

        assert response.status_code == 201
        assert response.get_json()["blocked_reason"] == "Spam"

    def test_create_without_blocked_reason_is_allowed(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 201

    def test_duplicate_email_returns_412(self, client, auth_header, existing_entry):
        response = client.post(
            "/blacklists",
            json={"email": "blocked@example.com", "app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 412
        assert "mensaje" in response.get_json()

    def test_missing_email_returns_400(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 400
        body = response.get_json()
        assert "email" in body["errors"]

    def test_missing_app_uuid_returns_400(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL},
            headers=auth_header,
        )

        assert response.status_code == 400
        body = response.get_json()
        assert "app_uuid" in body["errors"]

    def test_missing_both_required_fields_returns_400(self, client, auth_header):
        response = client.post("/blacklists", json={}, headers=auth_header)

        assert response.status_code == 400
        body = response.get_json()
        assert "email" in body["errors"]
        assert "app_uuid" in body["errors"]

    def test_invalid_email_format_returns_400(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": "notanemail", "app_uuid": VALID_UUID},
            headers=auth_header,
        )

        assert response.status_code == 400

    def test_invalid_app_uuid_returns_400(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": "not-a-valid-uuid"},
            headers=auth_header,
        )

        assert response.status_code == 400
        assert "mensaje" in response.get_json()

    def test_blocked_reason_exceeding_max_length_returns_400(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={
                "email": VALID_EMAIL,
                "app_uuid": VALID_UUID,
                "blocked_reason": "x" * 256,
            },
            headers=auth_header,
        )

        assert response.status_code == 400

    def test_x_forwarded_for_captured_as_ip(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
            headers={**auth_header, "X-Forwarded-For": "10.0.0.1"},
        )

        assert response.status_code == 201
        assert response.get_json()["ip_address"] == "10.0.0.1"

    def test_multiple_x_forwarded_for_uses_first_ip(self, client, auth_header):
        response = client.post(
            "/blacklists",
            json={"email": VALID_EMAIL, "app_uuid": VALID_UUID},
            headers={**auth_header, "X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
        )

        assert response.status_code == 201
        assert response.get_json()["ip_address"] == "10.0.0.1"
