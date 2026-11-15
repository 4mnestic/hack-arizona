import json
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path(__file__).with_name("nozzles.json")

# ASABE S572 droplet class -> the three classes the checks use.
ASABE_TO_DROPLET = {
    "extremely fine": "fine",
    "very fine": "fine",
    "fine": "fine",
    "medium": "medium",
    "coarse": "coarse",
    "very coarse": "coarse",
    "extremely coarse": "coarse",
    "ultra coarse": "coarse",
}


@dataclass
class Nozzle:
    name: str
    asabe_class: str
    vmd_microns: float | None = None
    pressure_psi: float | None = None
    kind: str = ""
    notes: str = ""

    @property
    def droplet_size(self) -> str:
        return ASABE_TO_DROPLET[self.asabe_class]


class LocalNozzleDB:
    """Nozzle catalog read from nozzles.json; lookups are case-insensitive."""

    def __init__(self, path: Path = DATA_FILE):
        raw = json.loads(Path(path).read_text())
        self._items = {n.name.lower(): n for n in (Nozzle(**r) for r in raw["nozzles"])}

    def list(self) -> list[str]:
        return [n.name for n in self._items.values()]

    def get(self, name: str) -> Nozzle:
        try:
            return self._items[name.lower()]
        except KeyError:
            raise KeyError(f"unknown nozzle {name!r}") from None
