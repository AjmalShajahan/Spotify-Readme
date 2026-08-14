import requests
from base64 import b64encode
from dotenv import find_dotenv, load_dotenv
from flask import Flask, Response, render_template, request, redirect
from os import getenv
from random import randint

REQUEST_TIMEOUT = (3.05, 10)

# Load environment variables
load_dotenv(find_dotenv())

# Define Base64 encoded images
with open("api/base64/placeholder_scan_code.txt") as f:
    B64_PLACEHOLDER_SCAN_CODE = f.read()
with open("api/base64/placeholder_image.txt") as f:
    B64_PLACEHOLDER_IMAGE = f.read()
with open("api/base64/spotify_logo.txt") as f:
    B64_SPOTIFY_LOGO = f.read()


def get_token():
    """Get a new access token"""
    required_variables = ("REFRESH_TOKEN", "CLIENT_ID", "CLIENT_SECRET")
    missing_variables = [name for name in required_variables if not getenv(name)]
    if missing_variables:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_variables)}"
        )

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": getenv("REFRESH_TOKEN"),
            "client_id": getenv("CLIENT_ID"),
            "client_secret": getenv("CLIENT_SECRET"),
        },
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    try:
        return r.json()["access_token"]
    except (KeyError, requests.exceptions.JSONDecodeError) as error:
        raise RuntimeError("Spotify token response did not contain an access token") from error


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
    r = requests.get(
        f"https://api.spotify.com/v1/{endpoint}",
        headers={"Authorization": f"Bearer {get_token()}"},
        timeout=REQUEST_TIMEOUT,
    )
    if not r.ok:
        raise Exception(f"Spotify API request failed ({r.status_code}): {r.text}")
    return parse_json_response(r)


def get_playback_track():
    """Get the current track, falling back to the most recently played track."""
    data = spotify_request("me/player/currently-playing")
    if data and data.get("item"):
        return data["item"]

    recent = spotify_request("me/player/recently-played?limit=1")
    items = recent.get("items", [])
    if not items:
        return None
    return items[0].get("track")


def generate_bars(bar_count, rainbow):
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
                background: {spectrum[i] if rainbow and rainbow != 'false' and rainbow != '0' else '#24D255'};
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
    item = get_playback_track()

    if not item:
        return render_template(
            "index.html",
            **{
                "bars": generate_bars(12, rainbow),
                "artist": "Spotify",
                "song": "Not Playing",
                "image": B64_PLACEHOLDER_IMAGE,
                "scan_code": None,
                "theme": theme,
                "spin": spin,
                "logo": B64_SPOTIFY_LOGO,
            },
        )

    album_images = item["album"]["images"]
    if not album_images:
        image = B64_PLACEHOLDER_IMAGE
    else:
        image_index = 1 if len(album_images) > 1 else 0
        image = load_image_base64(album_images[image_index]["url"])

    if scan and scan != "false" and scan != "0":
        bar_count = 10
        scan_code = get_scan_code(item["uri"])
    else:
        bar_count = 12
        scan_code = None

    return render_template(
        "index.html",
        **{
            "bars": generate_bars(bar_count, rainbow),
            "artist": item["artists"][0]["name"],
            "song": item["name"],
            "image": image,
            "scan_code": scan_code if scan_code != "" else B64_PLACEHOLDER_SCAN_CODE,
            "theme": theme,
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
            request.args.get("spin"),
            request.args.get("scan"),
            request.args.get("theme"),
            request.args.get("rainbow"),
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
    item = get_playback_track()
    if not item:
        response = redirect("https://open.spotify.com/")
    else:
        response = redirect(f"https://open.spotify.com/track/{item['id']}")
    response.headers["Cache-Control"] = "no-store"
    return response

if __name__ == "__main__":
    app.run()
