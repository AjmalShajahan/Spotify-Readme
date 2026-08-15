from types import SimpleNamespace

import pytest

from api import index


@pytest.fixture
def client():
    index.app.config.update(TESTING=True)
    return index.app.test_client()


@pytest.mark.parametrize(
    "is_playing,expected_status", [(True, "Now Playing"), (False, "Paused")]
)
def test_playback_reports_current_track_state(
    monkeypatch, is_playing, expected_status
):
    current = {"id": "current"}
    requests = []

    def fake_spotify_request(endpoint):
        requests.append(endpoint)
        return {"item": current, "is_playing": is_playing}

    monkeypatch.setattr(index, "spotify_request", fake_spotify_request)

    assert index.get_playback() == (current, expected_status)
    assert requests == ["me/player/currently-playing"]


def test_playback_falls_back_to_most_recent_track(monkeypatch):
    recent = {"id": "recent"}
    responses = iter(({}, {"items": [{"track": recent}]}))
    monkeypatch.setattr(index, "spotify_request", lambda _endpoint: next(responses))

    assert index.get_playback() == (recent, "Recently Played")


def test_playback_handles_empty_history(monkeypatch):
    monkeypatch.setattr(index, "spotify_request", lambda _endpoint: {})

    assert index.get_playback() == (None, "Not Playing")


@pytest.mark.parametrize(
    "artists,expected",
    [
        ([{"name": "Artist One"}], "Artist One"),
        (
            [{"name": "Artist One"}, {"name": "Artist Two"}],
            "Artist One, Artist Two",
        ),
        ([], "Unknown Artist"),
        ([{}], "Unknown Artist"),
    ],
)
def test_format_artists_includes_every_credit(artists, expected):
    assert index.format_artists({"artists": artists}) == expected


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
        "spin": True,
        "scan": True,
        "theme": "catppuccin-mocha",
        "rainbow": True,
    }


def test_health_endpoint_does_not_contact_spotify(client, monkeypatch):
    def unexpected_spotify_call():
        raise AssertionError("health endpoint contacted Spotify")

    monkeypatch.setattr(index, "get_playback", unexpected_spotify_call)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}
    assert response.mimetype == "application/json"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "spotify_available,expected_status,expected_json",
    [
        (True, 200, {"status": "ready", "spotify": "ok"}),
        (
            False,
            503,
            {"status": "unavailable", "spotify": "unavailable"},
        ),
    ],
)
def test_readiness_endpoint_reports_spotify_availability(
    client, monkeypatch, spotify_available, expected_status, expected_json
):
    if spotify_available:
        monkeypatch.setattr(
            index, "get_playback", lambda: (None, "Not Playing")
        )
    else:

        def unavailable():
            raise index.SpotifyAPIError("sensitive upstream detail")

        monkeypatch.setattr(index, "get_playback", unavailable)

    response = client.get("/api/ready")

    assert response.status_code == expected_status
    assert response.json == expected_json
    assert "sensitive" not in response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"


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
    monkeypatch.setattr(index, "get_playback", lambda: (None, "Not Playing"))

    with index.app.test_request_context("/api"):
        svg = index.make_svg(None, None, theme, None)

    assert background in svg
    assert "Not Playing" in svg


def test_rainbow_bars_use_spectrum_colors():
    bars = index.generate_bars(2, "true")

    assert bars.count("<div class='bar'></div>") == 2
    assert "#ff0000" in bars
    assert "#ff4000" in bars


def test_widget_honors_reduced_motion(monkeypatch):
    monkeypatch.setattr(index, "get_playback", lambda: (None, "Not Playing"))

    with index.app.test_request_context("/api"):
        svg = index.make_svg(True, False, "dark", True)

    assert "@media (prefers-reduced-motion: reduce)" in svg
    assert "animation: none !important" in svg
    assert "transform: scaleY(.65)" in svg


def test_access_token_is_reused_until_near_expiry(monkeypatch):
    calls = []

    class TokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "token", "expires_in": 3600}

    monkeypatch.setattr(index, "_access_token", None)
    monkeypatch.setattr(index, "_access_token_expires_at", 0.0)
    monkeypatch.setattr(index, "monotonic", lambda: 100.0)
    monkeypatch.setattr(index, "getenv", lambda _name: "configured")
    monkeypatch.setattr(
        index.requests,
        "post",
        lambda *args, **kwargs: calls.append((args, kwargs)) or TokenResponse(),
    )

    assert index.get_token() == "token"
    assert index.get_token() == "token"
    assert len(calls) == 1


def test_missing_credentials_raise_a_safe_spotify_error(monkeypatch):
    monkeypatch.setattr(index, "_access_token", None)
    monkeypatch.setattr(index, "_access_token_expires_at", 0.0)
    monkeypatch.setattr(index, "getenv", lambda _name: None)

    with pytest.raises(index.SpotifyAPIError, match="Missing required"):
        index.get_token()


def test_spotify_failure_renders_unavailable_placeholder(monkeypatch):
    def unavailable():
        raise index.SpotifyAPIError("unavailable")

    monkeypatch.setattr(index, "get_playback", unavailable)

    with index.app.test_request_context("/api"):
        svg = index.make_svg(False, False, "dark", False)

    assert "Unavailable" in svg
    assert "#161B22" in svg


@pytest.mark.parametrize("status", ["Now Playing", "Paused", "Recently Played"])
def test_widget_renders_playback_status(status, monkeypatch):
    track = {
        "album": {"images": []},
        "artists": [{"name": "Artist"}],
        "id": "track-id",
        "name": "Song",
        "uri": "spotify:track:track-id",
    }
    monkeypatch.setattr(index, "get_playback", lambda: (track, status))

    with index.app.test_request_context("/api"):
        svg = index.make_svg(False, False, "light", False)

    assert f'<span class="status">{status}</span>' in svg


def test_widget_renders_all_credited_artists(monkeypatch):
    track = {
        "album": {"images": []},
        "artists": [{"name": "Artist One"}, {"name": "Artist Two"}],
        "id": "track-id",
        "name": "Song",
        "uri": "spotify:track:track-id",
    }
    monkeypatch.setattr(index, "get_playback", lambda: (track, "Now Playing"))

    with index.app.test_request_context("/api"):
        svg = index.make_svg(False, False, "light", False)

    assert "Artist One, Artist Two" in svg


@pytest.mark.parametrize(
    "value,expected",
    [("true", True), ("1", True), ("false", False), ("0", False), (None, False)],
)
def test_parse_boolean(value, expected):
    assert index.parse_boolean(value) is expected


@pytest.mark.parametrize(
    "theme,expected",
    [
        ("catppuccin", "catppuccin-mocha"),
        ("catppuccin-latte", "catppuccin-latte"),
        ("unknown", "light"),
        (None, "light"),
    ],
)
def test_normalize_theme(theme, expected):
    assert index.normalize_theme(theme) == expected
