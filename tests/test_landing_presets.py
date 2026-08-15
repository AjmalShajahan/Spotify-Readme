from html.parser import HTMLParser
from pathlib import Path


LANDING_PAGE = Path(__file__).parent.parent / "public" / "index.html"


class PresetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.presets = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "button" and attributes.get("data-preset"):
            self.presets[attributes["data-preset"]] = {
                "theme": attributes.get("data-theme"),
                "effects": set(
                    filter(None, attributes.get("data-effects", "").split(","))
                ),
            }


def test_landing_page_exposes_curated_widget_presets():
    parser = PresetParser()
    parser.feed(LANDING_PAGE.read_text())

    assert parser.presets == {
        "clean": {"theme": "light", "effects": set()},
        "midnight": {"theme": "dark", "effects": set()},
        "catppuccin": {"theme": "catppuccin-mocha", "effects": set()},
        "spectrum": {"theme": "dark", "effects": {"spin", "rainbow"}},
    }
