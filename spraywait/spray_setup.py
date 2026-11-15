"""Turns the farmer's two choices (pesticide + nozzle) into the values the checks use."""

from dataclasses import replace

from spraywait.nozzles import LocalNozzleDB, Nozzle
from spraywait.pesticides import DEFAULT_PESTICIDE, LocalPesticideDB, Pesticide


def apply_nozzle(pesticide: Pesticide, nozzle: Nozzle | None) -> Pesticide:
    """The nozzle sets droplet size and pressure; everything else comes from the pesticide."""
    if nozzle is None:
        return pesticide
    return replace(
        pesticide,
        droplet_size=nozzle.droplet_size,
        nozzle=nozzle.name,
        vmd_microns=nozzle.vmd_microns,
        pressure_psi=nozzle.pressure_psi,
    )


class SpraySetup:
    """Looks up a pesticide and nozzle by name and combines them."""

    def __init__(self, pesticides: LocalPesticideDB | None = None, nozzles: LocalNozzleDB | None = None):
        self.pesticides = pesticides or LocalPesticideDB()
        self.nozzles = nozzles or LocalNozzleDB()

    def pesticide(self, name: str | None) -> Pesticide:
        if not name or name.lower() == DEFAULT_PESTICIDE.name.lower():
            return DEFAULT_PESTICIDE
        return self.pesticides.get(name)

    def resolve(self, pesticide: str | None, nozzle: str | None) -> Pesticide:
        """Raises KeyError for an unknown pesticide or nozzle name."""
        return apply_nozzle(self.pesticide(pesticide), self.nozzles.get(nozzle) if nozzle else None)
