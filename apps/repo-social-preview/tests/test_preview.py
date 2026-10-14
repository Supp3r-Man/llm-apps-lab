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

import github_repo
from compose import PREVIEW_SIZE, compose_preview, crop_to_size
from github_repo import RepoLookupError, clean_readme, fetch_repo, parse_repo
from nanobanana import ImageGenerationError, generate_image
from prompts import background_prompt

DARK = (20, 20, 30)


def make_png(size=(1600, 900), color=DARK) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def bright_columns(png: bytes, threshold=200):
    """x positions that contain near-white pixels (only text can produce them on a dark background)."""
    image = Image.open(io.BytesIO(png)).convert("L")
    xs = set()
    for x in range(image.width):
        if any(image.getpixel((x, y)) >= threshold for y in range(0, image.height, 2)):
            xs.add(x)
    return xs


def test_compose_outputs_exact_size_from_any_aspect_ratio():
    for source in [(1600, 900), (2100, 900), (1000, 1000)]:
        out = compose_preview(make_png(source), "repo", "desc")
        assert Image.open(io.BytesIO(out)).size == PREVIEW_SIZE


def test_text_is_drawn_on_the_left_and_stays_in_its_column():
    out = compose_preview(make_png(), "agent-lab", "Ten multi-agent apps adapted from open source", "Python · ★ 12")
    xs = bright_columns(out)
    assert xs, "no text pixels found"
    assert min(xs) >= 40  # respects the left margin
    assert max(xs) <= PREVIEW_SIZE[0] * 0.66  # never runs into the art on the right


def test_very_long_title_and_subtitle_do_not_overflow():
    title = "an-extraordinarily-long-repository-name-that-keeps-going-and-going-and-going"
    subtitle = "word " * 80
    out = compose_preview(make_png(), title, subtitle)
    xs = bright_columns(out)
    assert max(xs) <= PREVIEW_SIZE[0] * 0.66
    # Text must also stay clear of the top and bottom edges.
    gray = Image.open(io.BytesIO(out)).convert("L")
    rows = [y for y in range(gray.height) if any(gray.getpixel((x, y)) >= 200 for x in range(0, 800, 3))]
    assert rows and min(rows) >= 20 and max(rows) <= gray.height - 20


def test_hyphenated_repo_name_breaks_at_hyphens():
    from PIL import ImageDraw

    from compose import load_font, wrap

    name = "an-extraordinarily-long-repository-name-that-keeps-going"
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    small = load_font(36, bold=True)
    lines = wrap(draw, name, small, 717, max_lines=2)
    assert len(lines) == 2 and not any(line.endswith("…") for line in lines)
    assert "".join(lines) == name  # broke only after hyphens, lost nothing
    assert all(draw.textlength(line, font=small) <= 717 for line in lines)

    # Too big to fit in two lines: the last line is cut with an ellipsis.
    big = load_font(80, bold=True)
    cut = wrap(draw, name, big, 717, max_lines=2)
    assert len(cut) == 2 and cut[-1].endswith("…")


def test_long_hyphenated_title_shrinks_to_show_all_of_it(monkeypatch):
    import compose

    seen = []
    real_wrap = compose.wrap

    def spy(draw, text, font, max_width, max_lines):
        lines = real_wrap(draw, text, font, max_width, max_lines)
        if text.startswith("an-extra"):
            seen.append((font.size, lines))
        return lines

    monkeypatch.setattr(compose, "wrap", spy)
    compose.compose_preview(make_png(), "an-extraordinarily-long-repository-name-that-keeps-going", "x")
    size, lines = seen[-1]
    assert not any(line.endswith("…") for line in lines)
    assert size < round(PREVIEW_SIZE[1] * 0.16)  # it did shrink
    assert size > 36  # but not to the floor


def test_text_changes_the_image_but_background_alone_has_none():
    assert not bright_columns(compose_preview(make_png(), "", ""))
    assert bright_columns(compose_preview(make_png(), "hello", ""))


def test_crop_to_size_is_centered():
    left = Image.new("RGB", (800, 900), (255, 0, 0))
    wide = Image.new("RGB", (2400, 900), (0, 0, 255))
    wide.paste(left, (800, 0))  # red band exactly in the middle third
    buf = io.BytesIO()
    wide.save(buf, "PNG")
    cropped = crop_to_size(buf.getvalue(), PREVIEW_SIZE)
    center = cropped.getpixel((PREVIEW_SIZE[0] // 2, PREVIEW_SIZE[1] // 2))
    assert center[0] > 200 and center[2] < 60


@pytest.mark.parametrize(
    "text, expected",
    [
        ("octocat/Hello-World", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
        ("github.com/octocat/Hello-World.git", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World/tree/main/docs", ("octocat", "Hello-World")),
    ],
)
def test_parse_repo(text, expected):
    assert parse_repo(text) == expected


@pytest.mark.parametrize("text", ["octocat", "", "a b/c", "owner/na me"])
def test_parse_repo_rejects_bad_input(text):
    with pytest.raises(RepoLookupError):
        parse_repo(text)


def test_clean_readme_strips_markup_and_truncates():
    md = "# Title\n\n![badge](http://x/y.svg) [Docs](http://docs) <b>bold</b>\n\n```py\nprint(1)\n```\n" + "word " * 500
    out = clean_readme(md, limit=100)
    assert out.startswith("Title Docs bold")
    assert "print" not in out and "http" not in out and "<" not in out
    assert len(out) <= 100


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self.ok = status < 400
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def test_fetch_repo_combines_repo_and_readme(monkeypatch):
    def fake_get(url, headers=None, timeout=None, params=None):
        if url.endswith("/readme"):
            assert "raw" in headers["Accept"]
            return FakeResponse(text="# Hello\nA demo project.")
        return FakeResponse(
            payload={
                "full_name": "octocat/Hello-World",
                "name": "Hello-World",
                "description": "My first repo",
                "language": "Python",
                "topics": ["demo"],
                "stargazers_count": 1234,
            }
        )

    monkeypatch.setattr(github_repo.requests, "get", fake_get)
    info = fetch_repo("octocat", "Hello-World")
    assert info["name"] == "Hello-World" and info["stars"] == 1234
    assert info["readme_excerpt"] == "Hello A demo project."


def test_fetch_repo_404_and_rate_limit(monkeypatch):
    monkeypatch.setattr(github_repo.requests, "get", lambda *a, **k: FakeResponse(404))
    with pytest.raises(RepoLookupError, match="not found"):
        fetch_repo("o", "n")
    monkeypatch.setattr(github_repo.requests, "get", lambda *a, **k: FakeResponse(403))
    with pytest.raises(RepoLookupError, match="rate limit"):
        fetch_repo("o", "n")


def test_background_prompt_forbids_text_and_includes_context():
    info = {
        "name": "agent-lab",
        "description": "Multi-agent apps",
        "language": "Python",
        "topics": ["llm", "agents"],
        "readme_excerpt": "Ten apps",
    }
    p = background_prompt(info, "Circuit board")
    assert "Do not include any text" in p
    assert "agent-lab" in p and "Multi-agent apps" in p and "llm, agents" in p and "Ten apps" in p
    assert "circuit-board" in p


def google_client(handler):
    return genai.Client(
        api_key="test",
        http_options=types.HttpOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(handler))),
    )


def image_response(png: bytes):
    return httpx.Response(
        200,
        json={
            "id": "int_1",
            "status": "completed",
            "steps": [
                {
                    "type": "model_output",
                    "content": [{"type": "image", "mime_type": "image/png", "data": base64.b64encode(png).decode()}],
                }
            ],
        },
    )


def test_background_request_uses_16_9_and_surfaces_errors():
    seen = []

    def ok(request):
        seen.append(json.loads(request.content))
        return image_response(make_png())

    generate_image(google_client(ok), "bg", aspect_ratio="16:9", image_size="1K")
    assert seen[0]["response_format"]["aspect_ratio"] == "16:9"

    def denied(request):
        return httpx.Response(403, json={"error": {"code": 403, "message": "no", "status": "PERMISSION_DENIED"}})

    with pytest.raises(ImageGenerationError, match="rejected"):
        generate_image(google_client(denied), "bg")


def test_full_flow_through_the_ui(monkeypatch):
    from streamlit.testing.v1 import AppTest

    prompts = []

    def handler(request):
        prompts.append(json.loads(request.content)["input"])
        return image_response(make_png())

    real_client = genai.Client
    monkeypatch.setattr(
        genai,
        "Client",
        lambda api_key=None: real_client(
            api_key=api_key,
            http_options=types.HttpOptions(httpx_client=httpx.Client(transport=httpx.MockTransport(handler))),
        ),
    )

    def fake_get(url, headers=None, timeout=None, params=None):
        if url.endswith("/readme"):
            return FakeResponse(text="# Hello\nA demo project.")
        return FakeResponse(
            payload={
                "full_name": "octocat/Hello-World",
                "name": "Hello-World",
                "description": "My first repo",
                "language": "Python",
                "topics": [],
                "stargazers_count": 5,
            }
        )

    monkeypatch.setattr(github_repo.requests, "get", fake_get)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    at = AppTest.from_file(app, default_timeout=60).run()
    assert not at.exception

    at.sidebar.text_input[0].set_value("test-key")
    [t for t in at.text_input if t.label == "Public repo"][0].set_value("octocat/Hello-World")
    at.run()
    [b for b in at.button if b.label == "Fetch repo"][0].click()
    at.run()
    assert not at.exception and not at.error
    assert at.session_state["title"] == "Hello-World"
    assert at.session_state["subtitle"] == "My first repo"
    assert at.session_state["meta"] == "Python · 5 stars"
    # Fonts such as Segoe UI have no star glyph, so the footer must stay in plain characters.
    assert all(ord(c) < 128 or c == "·" for c in at.session_state["meta"])

    [b for b in at.button if b.label == "Generate background"][0].click()
    at.run()
    assert not at.exception and not at.error
    assert len(prompts) == 1 and "Hello-World" in prompts[0] and "Do not include any text" in prompts[0]
    assert at.session_state["background"] is not None

    # Editing the text must not trigger another model call.
    [t for t in at.text_input if t.label == "Title"][0].set_value("Renamed")
    at.run()
    assert len(prompts) == 1 and not at.exception
