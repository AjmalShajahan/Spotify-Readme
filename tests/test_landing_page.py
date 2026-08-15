from html.parser import HTMLParser
from pathlib import Path
from struct import unpack


ROOT = Path(__file__).parent.parent
LANDING_PAGE = ROOT / "public" / "index.html"
PREVIEW_IMAGE = ROOT / "public" / "og-preview.png"
PRODUCTION_URL = "https://ajmal-spotify-readme.vercel.app/"


class HeadMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metadata = {}
        self.links = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            if key:
                self.metadata[key] = attributes.get("content")
        elif tag == "link" and attributes.get("rel"):
            self.links[attributes["rel"]] = attributes.get("href")


def parse_head_metadata():
    parser = HeadMetadataParser()
    parser.feed(LANDING_PAGE.read_text())
    return parser


def test_landing_page_has_complete_share_metadata():
    parser = parse_head_metadata()
    preview_url = f"{PRODUCTION_URL}og-preview.png"

    assert parser.links["canonical"] == PRODUCTION_URL
    assert parser.metadata["og:type"] == "website"
    assert parser.metadata["og:url"] == PRODUCTION_URL
    assert parser.metadata["og:image"] == preview_url
    assert parser.metadata["og:image:width"] == "1200"
    assert parser.metadata["og:image:height"] == "630"
    assert parser.metadata["og:image:alt"]
    assert parser.metadata["twitter:card"] == "summary_large_image"
    assert parser.metadata["twitter:image"] == preview_url
    assert parser.metadata["twitter:image:alt"]


def test_share_preview_is_a_1200_by_630_png():
    data = PREVIEW_IMAGE.read_bytes()

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert unpack(">II", data[16:24]) == (1200, 630)
