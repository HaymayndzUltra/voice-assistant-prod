import time

import pytest

from common.api.contract import (
    APIHeader,
    APIResponse,
    APIMessage,
    Priority,
    MessageType,
    create_request,
)
from common.pools.http_pool import HTTPConfig


class TestAPIContract:
    """Light-weight sanity checks for the common.api.contract helpers.

    These tests do not spin up full middleware/processor stacks – they
    simply ensure the dataclass helpers serialize / deserialize properly
    so that higher-level integration tests can rely on them.
    """

    def test_header_roundtrip(self):
        header = APIHeader(
            source_agent="Tester",
            target_agent="Receiver",
            priority=Priority.HIGH,
            timeout=5.0,
        )
        as_dict = header.to_dict()
        # Simulate JSON round-trip
        recreated = APIHeader.from_dict(as_dict)
        # Fields that should survive round-trip exactly
        assert recreated.source_agent == header.source_agent
        assert recreated.target_agent == header.target_agent
        assert recreated.priority == header.priority
        # timestamp may differ slightly depending on from_dict defaulting – ensure close
        assert abs(recreated.timestamp - header.timestamp) < 1.0

    def test_response_helpers(self):
        resp_ok = APIResponse.success({"answer": 42})
        assert resp_ok.status.value == "success"
        assert resp_ok.data == {"answer": 42}

        resp_err = APIResponse.error("boom", "E123")
        assert resp_err.status.value == "error"
        assert resp_err.error_code == "E123"

    def test_create_request_helper(self):
        msg = create_request(
            source_agent="UnitTestAgent",
            target_agent="ModelManagerAgent",
            endpoint="/v1/reasoning/generate",
            data={"prompt": "Hello"},
            priority=Priority.LOW,
            timeout=15.0,
        )
        assert isinstance(msg, APIMessage)
        # basic envelope checks
        assert msg.payload["endpoint"] == "/v1/reasoning/generate"
        assert msg.header.message_type == MessageType.REQUEST
        assert msg.header.priority == Priority.LOW

    def test_httpconfig_scheme_autofill(self):
        cfg = HTTPConfig(base_url="api.openai.com")
        assert cfg.base_url.startswith("https://")
