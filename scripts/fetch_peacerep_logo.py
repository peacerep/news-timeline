"""Bundle the PeaceRep logo from the project's published logo library."""

from pathlib import Path
from urllib.request import urlopen


SOURCE = "https://peacerep.github.io/logos/img/PeaceRep_nobg.png"
DESTINATION = Path(__file__).resolve().parents[1] / "assets/brand/peacerep-logo.png"


def main():
    with urlopen(SOURCE, timeout=30) as response:
        content = response.read()
    assert content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) > 5_000
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_bytes(content)
    print(f"Saved PeaceRep logo ({len(content)} bytes)")


if __name__ == "__main__":
    main()
