import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path(__file__).with_name("pesticides.json")


@dataclass
class Pesticide:
    name: str
    category: str = ""
    product_examples: str = ""
    vapor_pressure_mpa: float | None = None
    volatility: str = "low"  # low | moderate | high
    droplet_size: str = "medium"  # fine | medium | coarse
    min_wind_mph: float = 3.0
    max_wind_mph: float = 10.0
    max_temp_f: float | None = None
    notes: str = ""


DEFAULT_PESTICIDE = Pesticide(
    name="Generic (label defaults)",
    notes="Uses the common 3-10 mph guidance. Always confirm against the actual label.",
)


class PesticideDB(ABC):
    @abstractmethod
    def list(self) -> list[str]:
        """Names of every known pesticide."""

    @abstractmethod
    def get(self, name: str) -> Pesticide:
        """Look up one pesticide by name (case-insensitive)."""


class LocalPesticideDB(PesticideDB):
    def __init__(self, path: Path = DATA_FILE):
        raw = json.loads(Path(path).read_text())
        self._items = {p.name.lower(): p for p in (Pesticide(**r) for r in raw["pesticides"])}

    def list(self) -> list[str]:
        return [p.name for p in self._items.values()]

    def get(self, name: str) -> Pesticide:
        try:
            return self._items[name.lower()]
        except KeyError:
            raise KeyError(f"unknown pesticide {name!r}") from None
