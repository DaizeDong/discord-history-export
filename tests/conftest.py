"""Isolate mocked transport tests from the native Git fixture environment."""
import os
from pathlib import Path

import pytest


MOCKED_TRANSPORT_MODULES = {
    Path(__file__).parent / "test_export.py",
    Path(__file__).parent / "test_ssh_alias.py",
}


@pytest.fixture(autouse=True)
def isolated_mocked_transport_environment(request, monkeypatch):
    if request.path not in MOCKED_TRANSPORT_MODULES:
        return
    # Clear only ambient overrides. Test-body mutations must still reach the guard.
    for key, value in tuple(os.environ.items()):
        upper = key.upper()
        if (upper.startswith("GIT_") and upper != "GIT_OPTIONAL_LOCKS") or upper in {
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "SSH_COMMAND",
                "SSL_CERT_FILE", "SSL_CERT_DIR", "CURL_CA_BUNDLE", "CURL_SSL_BACKEND"}:
            monkeypatch.delenv(key, raising=False)
        elif upper == "GH_HOST" and value.lower() != "github.com":
            monkeypatch.delenv(key, raising=False)
