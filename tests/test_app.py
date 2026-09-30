"""UI smoke test: the app renders its four tabs without an exception (no claim open)."""
import pytest


def test_app_renders():
    pytest.importorskip("cv2")
    testing = pytest.importorskip("streamlit.testing.v1")
    at = testing.AppTest.from_file("claimshield/ui/app.py", default_timeout=120).run()
    assert not at.exception
    assert len(at.tabs) == 4
