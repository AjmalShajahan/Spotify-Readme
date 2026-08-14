from types import SimpleNamespace

import pytest

from api import index


@pytest.fixture
def client():
    index.app.config.update(TESTING=True)
    return index.app.test_client()


def test_playback_prefers_current_track(monkeypatch):
    current = {"id": "current"}
    requests = []

    def fake_spotify_request(endpoint):
        requests.append(endpoint)
        return {"item": current}

    monkeypatch.setattr(index, "spotify_request", fake_spotify_request)

    assert index.get_playback_track() == current
    assert requests == ["me/player/currently-playing"]


def test_playback_falls_back_to_most_recent_track(monkeypatch):
    recent = {"id": "recent"}
    responses = iter(({}, {"items": [{"track": recent}]}))
    monkeypatch.setattr(index, "spotify_request", lambda _endpoint: next(responses))

    assert index.get_playback_track() == recent


def test_playback_handles_empty_history(monkeypatch):
    monkeypatch.setattr(index, "spotify_request", lambda _endpoint: {})

    assert index.get_playback_track() is None


@pytest.mark.parametrize("status_code,content", [(204, b""), (200, b"")])
def test_parse_json_response_handles_empty_bodies(status_code, content):
    response = SimpleNamespace(status_code=status_code, content=content)

    assert index.parse_json_response(response) == {}


def test_parse_json_response_handles_invalid_json():
    response = SimpleNamespace(status_code=200, content=b"not-json")

    def invalid_json():
        raise index.requests.exceptions.JSONDecodeError("invalid", "not-json", 0)

    response.json = invalid_json

    assert index.parse_json_response(response) == {}


def test_widget_route_passes_supported_options_and_sets_cache_headers(
    client, monkeypatch
):
    captured = {}

    def fake_make_svg(spin, scan, theme, rainbow):
        captured.update(spin=spin, scan=scan, theme=theme, rainbow=rainbow)
        return "<svg></svg>"

    monkeypatch.setattr(index, "make_svg", fake_make_svg)

    response = client.get(
        "/api?spin=true&scan=true&theme=catppuccin-mocha&rainbow=true"
    )

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert response.headers["Cache-Control"] == (
        "public, max-age=0, s-maxage=5, stale-while-revalidate=25"
    )
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert captured == {
        "spin": "true",
        "scan": "true",
        "theme": "catppuccin-mocha",
        "rainbow": "true",
    }


@pytest.mark.parametrize(
    "track,expected_location",
    [
        ({"id": "track-id"}, "https://open.spotify.com/track/track-id"),
        (None, "https://open.spotify.com/"),
    ],
)
def test_play_redirects_to_spotify(client, monkeypatch, track, expected_location):
    monkeypatch.setattr(index, "get_playback_track", lambda: track)

    response = client.get("/api/play")

    assert response.status_code == 302
    assert response.headers["Location"] == expected_location
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "theme,background",
    [
        ("catppuccin-latte", "#eff1f5"),
        ("catppuccin-frappe", "#303446"),
        ("catppuccin-macchiato", "#24273a"),
        ("catppuccin-mocha", "#1e1e2e"),
        ("catppuccin", "#1e1e2e"),
    ],
)
def test_catppuccin_themes_render(theme, background, monkeypatch):
    monkeypatch.setattr(index, "get_playback_track", lambda: None)

    with index.app.test_request_context("/api"):
        svg = index.make_svg(None, None, theme, None)

    assert background in svg
    assert "Not Playing" in svg


def test_rainbow_bars_use_spectrum_colors():
    bars = index.generate_bars(2, "true")

    assert bars.count("<div class='bar'></div>") == 2
    assert "#ff0000" in bars
    assert "#ff4000" in bars
