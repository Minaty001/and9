import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ["AND9_INSTALLED_APPS_PATH"] = "/tmp/non_existent_installed_apps.json"
    yield
