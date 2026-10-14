import base64
import io
import json
import os
import sys

import httpx
import pytest
from google import genai
from google.genai import types
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import github_profile
from nanobanana import ImageGenerationError, fit_to_width, generate_image
from prompts import banner_prompt, edit_prompt


def make_png(size=(40, 10), color=(200, 30, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def client_with(handler):
    transport = httpx.MockTransport(handler)
    return genai.Client(api_key="test", http_options=types.HttpOptions(httpx_client=httpx.Client(transport=transport)))


def image_response(png: bytes, interaction_id="int_1"):
    return httpx.Response(
        200,
        json={
            "id": interaction_id,
            "status": "completed",
            "steps": [
                {
                    "type": "model_output",
                    "content": [{"type": "image", "mime_type": "image/png", "data": base64.b64encode(png).decode()}],
                }
            ],
        },
    )


def test_generate_sends_expected_request_and_decodes_image():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return image_response(make_png())

    result = generate_image(client_with(handler), "a banner", aspect_ratio="4:1", image_size="2K")
    assert seen[0]["input"] == "a banner"
    assert seen[0]["response_format"] == {
        "type": "image",
        "mime_type": "image/png",
        "aspect_ratio": "4:1",
        "image_size": "2K",
    }
    assert "previous_interaction_id" not in seen[0]
    assert result.interaction_id == "int_1"
    assert Image.open(io.BytesIO(result.png)).size == (40, 10)


def test_edit_sends_previous_interaction_id():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return image_response(make_png(), interaction_id="int_2")

    result = generate_image(client_with(handler), "darker", previous_interaction_id="int_1")
    assert seen[0]["previous_interaction_id"] == "int_1"
    assert result.interaction_id == "int_2"


@pytest.mark.parametrize(
    "status, expected",
    [(401, "rejected"), (403, "rejected"), (404, "Model not found"), (429, "Rate limit")],
)
def test_http_errors_become_friendly_messages(status, expected):
    def handler(request):
        return httpx.Response(status, json={"error": {"code": status, "message": "nope", "status": "X"}})

    with pytest.raises(ImageGenerationError) as err:
        generate_image(client_with(handler), "x")
    assert expected in str(err.value)


def test_response_without_image_is_reported():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "id": "int_3",
                "status": "completed",
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": "I cannot draw that."}]}],
            },
        )

    with pytest.raises(ImageGenerationError) as err:
        generate_image(client_with(handler), "x")
    assert "no image" in str(err.value)
    assert "I cannot draw that." in str(err.value)


def test_fit_to_width_keeps_aspect_ratio():
    out = fit_to_width(make_png((400, 100)), 1500)
    assert Image.open(io.BytesIO(out)).size == (1500, 375)


def test_prompts_contain_exact_text_and_edit_keeps_rest():
    p = banner_prompt("Ada Lovelace", "Building agents", ["Python", "Go"], "Clean dark")
    assert '"Ada Lovelace"' in p and '"Building agents"' in p and "Python, Go" in p
    assert "Keep everything else" in edit_prompt("Make it darker")
    # No tagline: the prompt must not mention one. Unknown styles pass through verbatim.
    bare = banner_prompt("Ada", "", [], "isometric")
    assert "tagline" not in bare and "isometric" in bare


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.ok = status < 400
        self._payload = payload

    def json(self):
        return self._payload


def test_lookup_profile_counts_languages_and_skips_forks(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/users/octocat"):
            return FakeResponse(payload={"login": "octocat", "name": "The Octocat", "bio": "Hi"})
        return FakeResponse(
            payload=[
                {"language": "Python", "fork": False},
                {"language": "Python", "fork": False},
                {"language": "Go", "fork": False},
                {"language": "Rust", "fork": True},
                {"language": None, "fork": False},
            ]
        )

    monkeypatch.setattr(github_profile.requests, "get", fake_get)
    info = github_profile.lookup_profile("@octocat")
    assert info == {"handle": "octocat", "name": "The Octocat", "bio": "Hi", "languages": ["Python", "Go"]}


def test_lookup_profile_rejects_bad_handles_and_reports_404(monkeypatch):
    with pytest.raises(github_profile.GitHubLookupError):
        github_profile.lookup_profile("not a handle!")
    monkeypatch.setattr(github_profile.requests, "get", lambda *a, **k: FakeResponse(404))
    with pytest.raises(github_profile.GitHubLookupError) as err:
        github_profile.lookup_profile("ghost")
    assert "No GitHub user" in str(err.value)


def test_app_starts_without_key_and_blocks_generation(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    at = AppTest.from_file(app, default_timeout=60).run()
    assert not at.exception
    assert [b for b in at.button if b.label == "Generate banner"][0].disabled
    assert any("API key" in i.value for i in at.info)


def test_generate_then_edit_through_the_ui(monkeypatch):
    from streamlit.testing.v1 import AppTest

    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return image_response(make_png((400, 100)), interaction_id=f"int_{len(seen)}")

    real_client = genai.Client
    monkeypatch.setattr(
        genai,
        "Client",
        lambda api_key=None: real_client(
            api_key=api_key, http_options=types.HttpOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(handler)))
        ),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    at = AppTest.from_file(app, default_timeout=60).run()

    at.sidebar.text_input[0].set_value("test-key")
    [t for t in at.text_input if t.label == "Name on the banner"][0].set_value("Ada Lovelace")
    at.run()
    [b for b in at.button if b.label == "Generate banner"][0].click()
    at.run()
    assert not at.exception and not at.error
    assert len(seen) == 1 and "Ada Lovelace" in seen[0]["input"]
    assert len(at.session_state["history"]) == 1

    [t for t in at.text_input if t.label == "Describe a change"][0].set_value("Make it darker")
    at.run()
    [b for b in at.button if b.label == "Apply change"][0].click()
    at.run()
    assert not at.exception and not at.error
    assert len(seen) == 2
    assert seen[1]["previous_interaction_id"] == "int_1"
    assert "Make it darker" in seen[1]["input"]
    assert len(at.session_state["history"]) == 2
