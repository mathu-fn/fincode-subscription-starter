"""redaction.scrub の単体テスト。

構造化ログと監査ログが共有する秘匿処理。「カード情報・トークン・JWT・
シークレットをログに出さない」不変条件の中核なので、キー集合と再帰挙動を固定する。
"""

from __future__ import annotations

from app.core.redaction import scrub


def test_scrub_masks_sensitive_keys() -> None:
    scrubbed = scrub(
        {
            "password": "hunter2",
            "token": "tok_secret",
            "credential": "eyJhbGciOi...",
            "id_token": "eyJhbGciOi...",
            "authorization": "Bearer xxx",
            "card_number": "4242424242424242",
            "cvc": "123",
            "fincode_response": {"raw": "body"},
            "api_key": "m_test_xxx",
        }
    )
    assert all(v == "***" for v in scrubbed.values()), scrubbed


def test_scrub_recurses_into_nested_structures() -> None:
    scrubbed = scrub(
        {
            "user": {"email": "a@example.com", "password": "x"},
            "items": [{"token": "t1"}, {"amount": 500}],
        }
    )
    assert scrubbed["user"]["password"] == "***"
    assert scrubbed["user"]["email"] == "a@example.com"
    assert scrubbed["items"][0]["token"] == "***"
    assert scrubbed["items"][1]["amount"] == 500


def test_scrub_matches_case_insensitively_but_exactly() -> None:
    scrubbed = scrub({"Authorization": "Bearer xxx", "card_brand": "VISA"})
    assert scrubbed["Authorization"] == "***"
    # 部分一致はしない: card_brand は非機微。
    assert scrubbed["card_brand"] == "VISA"


def test_scrub_passes_through_scalars() -> None:
    assert scrub("plain") == "plain"
    assert scrub(42) == 42
    assert scrub(None) is None
