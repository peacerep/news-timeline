"""Bundle Montserrat and its OFL licence from the official Google Fonts repository."""

from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1] / "assets/fonts"
FILES = {
    "Montserrat-Variable.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/OFL.txt",
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for filename, url in FILES.items():
        with urlopen(url, timeout=30) as response:
            content = response.read()
        if filename.endswith(".ttf"):
            assert content[:4] in (b"\x00\x01\x00\x00", b"OTTO") and len(content) > 100_000
        else:
            assert b"SIL OPEN FONT LICENSE" in content.upper()
        (ROOT / filename).write_bytes(content)
        print(f"Saved {filename} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
