import requests
from base64 import b64encode
from dotenv import find_dotenv, load_dotenv
from flask import Flask, Response, render_template, request, redirect
from os import getenv
from random import randint
from time import monotonic

REQUEST_TIMEOUT = (3.05, 10)
TOKEN_EXPIRY_BUFFER_SECONDS = 30

_access_token = None
_access_token_expires_at = 0.0

# Load environment variables
load_dotenv(find_dotenv())

# Define Base64 encoded images
with open("api/base64/placeholder_scan_code.txt") as f:
    B64_PLACEHOLDER_SCAN_CODE = f.read()
with open("api/base64/placeholder_image.txt") as f:
    B64_PLACEHOLDER_IMAGE = f.read()
with open("api/base64/spotify_logo.txt") as f:
    B64_SPOTIFY_LOGO = f.read()

CATPPUCCIN_THEMES = {
    "catppuccin-latte": {
        "background": "#eff1f5",
        "shadow": "#dce0e8",
        "text": "#4c4f69",
        "subtext": "#6c6f85",
        "bar": "#40a02b",
        "dark": False,
    },
    "catppuccin-frappe": {
        "background": "#303446",
        "shadow": "#292c3c",
        "text": "#c6d0f5",
        "subtext": "#a5adce",
        "bar": "#a6d189",
        "dark": True,
    },
    "catppuccin-macchiato": {
        "background": "#24273a",
        "shadow": "#1e2030",
        "text": "#cad3f5",
        "subtext": "#a5adcb",
        "bar": "#a6da95",
        "dark": True,
    },
    "catppuccin-mocha": {
        "background": "#1e1e2e",
        "shadow": "#181825",
        "text": "#cdd6f4",
        "subtext": "#a6adc8",
        "bar": "#a6e3a1",
        "dark": True,
    },
}

SUPPORTED_THEMES = {"light", "dark", *CATPPUCCIN_THEMES}


class SpotifyAPIError(RuntimeError):
    """Raised when Spotify cannot provide a usable response."""


def parse_boolean(value):
    """Treat documented truthy values as enabled and everything else as disabled."""
    return str(value).lower() in {"1", "true"}


def normalize_theme(theme):
    """Return a supported canonical theme, falling back to light."""
    if theme == "catppuccin":
        return "catppuccin-mocha"
    return theme if theme in SUPPORTED_THEMES else "light"


def get_token():
    """Get a new access token"""
    global _access_token, _access_token_expires_at

    if _access_token and monotonic() < _access_token_expires_at:
        return _access_token

    required_variables = ("REFRESH_TOKEN", "CLIENT_ID", "CLIENT_SECRET")
    missing_variables = [name for name in required_variables if not getenv(name)]
    if missing_variables:
        raise SpotifyAPIError(
            f"Missing required environment variables: {', '.join(missing_variables)}"
        )

    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": getenv("REFRESH_TOKEN"),
                "client_id": getenv("CLIENT_ID"),
                "client_secret": getenv("CLIENT_SECRET"),
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        _access_token = payload["access_token"]
        lifetime = max(int(payload.get("expires_in", 3600)), 0)
    except (
        KeyError,
        TypeError,
        ValueError,
        requests.exceptions.RequestException,
    ) as error:
        raise SpotifyAPIError("Unable to refresh the Spotify access token") from error

    _access_token_expires_at = monotonic() + max(
        lifetime - TOKEN_EXPIRY_BUFFER_SECONDS, 0
    )
    return _access_token


def parse_json_response(response):
    """Return JSON response data, or an empty dict for empty/non-JSON bodies."""
    if response.status_code == 204 or not response.content:
        return {}
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {}


def spotify_request(endpoint):
    """Make a request to the specified endpoint"""
    try:
        response = requests.get(
            f"https://api.spotify.com/v1/{endpoint}",
            headers={"Authorization": f"Bearer {get_token()}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise SpotifyAPIError("Spotify API request failed") from error
    return parse_json_response(response)


def get_playback():
    """Return a track and an accurate description of its playback state."""
    data = spotify_request("me/player/currently-playing")
    if data and data.get("item"):
        status = "Now Playing" if data.get("is_playing") else "Paused"
        return data["item"], status

    recent = spotify_request("me/player/recently-played?limit=1")
    items = recent.get("items", [])
    if not items:
        return None, "Not Playing"
    return items[0].get("track"), "Recently Played"


def get_playback_track():
    """Return only the current or most recently played track."""
    track, _status = get_playback()
    return track


def format_artists(item):
    """Return every credited artist as a readable, comma-separated string."""
    artists = item.get("artists", [])
    names = [artist.get("name") for artist in artists if artist.get("name")]
    return ", ".join(names) if names else "Unknown Artist"


def generate_bars(bar_count, rainbow, color="#24D255"):
    """Build the HTML/CSS snippets for the EQ bars to be injected"""
    bars = "".join(["<div class='bar'></div>" for _ in range(bar_count)])
    css = "<style>"
    if rainbow and rainbow != "false" and rainbow != "0":
        css += ".bar-container { animation-duration: 2s; }"
    spectrum = [
        "#ff0000",
        "#ff4000",
        "#ff8000",
        "#ffbf00",
        "#ffff00",
        "#bfff00",
        "#80ff00",
        "#40ff00",
        "#00ff00",
        "#00ff40",
        "#00ff80",
        "#00ffbf",
        "#00ffff",
        "#00bfff",
        "#0080ff",
        "#0040ff",
        "#0000ff",
        "#4000ff",
        "#8000ff",
        "#bf00ff",
        "#ff00ff",
    ]
    for i in range(bar_count):
        css += f""".bar:nth-child({i + 1}) {{
                animation-duration: {randint(500, 750)}ms;
                background: {spectrum[i] if rainbow and rainbow != 'false' and rainbow != '0' else color};
            }}"""
    return f"{bars}{css}</style>"


def load_image_base64(url):
    """Get the Base64 encoded image from url"""
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return b64encode(response.content).decode("ascii")


def get_scan_code(spotify_uri):
    """Get the track code for a song"""
    return load_image_base64(
        f"https://scannables.scdn.co/uri/plain/png/000000/white/640/{spotify_uri}"
    )


def make_svg(spin, scan, theme, rainbow):
    """Render the HTML template with variables"""
    theme = normalize_theme(theme)
    try:
        item, playback_status = get_playback()
    except SpotifyAPIError:
        item = None
        playback_status = "Unavailable"

    palette = CATPPUCCIN_THEMES.get(theme)
    bar_color = palette["bar"] if palette else "#24D255"

    if not item:
        return render_template(
            "index.html",
            **{
                "bars": generate_bars(12, rainbow, bar_color),
                "artist": "Spotify",
                "song": (
                    "Unavailable"
                    if playback_status == "Unavailable"
                    else "Not Playing"
                ),
                "playback_status": playback_status,
                "image": B64_PLACEHOLDER_IMAGE,
                "scan_code": None,
                "theme": theme,
                "palette": palette,
                "spin": spin,
                "logo": B64_SPOTIFY_LOGO,
            },
        )

    album_images = item["album"]["images"]
    if not album_images:
        image = B64_PLACEHOLDER_IMAGE
    else:
        image_index = 1 if len(album_images) > 1 else 0
        try:
            image = load_image_base64(album_images[image_index]["url"])
        except requests.exceptions.RequestException:
            image = B64_PLACEHOLDER_IMAGE

    if scan:
        bar_count = 10
        try:
            scan_code = get_scan_code(item["uri"])
        except requests.exceptions.RequestException:
            scan_code = B64_PLACEHOLDER_SCAN_CODE
    else:
        bar_count = 12
        scan_code = None

    return render_template(
        "index.html",
        **{
            "bars": generate_bars(bar_count, rainbow, bar_color),
            "artist": format_artists(item),
            "song": item["name"],
            "playback_status": playback_status,
            "image": image,
            "scan_code": scan_code if scan_code != "" else B64_PLACEHOLDER_SCAN_CODE,
            "theme": theme,
            "palette": palette,
            "spin": spin,
            "logo": B64_SPOTIFY_LOGO,
        },
    )


app = Flask(__name__)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    resp = Response(
        make_svg(
            parse_boolean(request.args.get("spin")),
            parse_boolean(request.args.get("scan")),
            request.args.get("theme"),
            parse_boolean(request.args.get("rainbow")),
        ),
        mimetype="image/svg+xml",
    )
    resp.headers["Cache-Control"] = (
        "public, max-age=0, s-maxage=5, stale-while-revalidate=25"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/play")
@app.route("/api/play")
def play():
    try:
        item = get_playback_track()
    except SpotifyAPIError:
        item = None
    if not item:
        response = redirect("https://open.spotify.com/")
    else:
        response = redirect(f"https://open.spotify.com/track/{item['id']}")
    response.headers["Cache-Control"] = "no-store"
    return response

if __name__ == "__main__":
    app.run()
