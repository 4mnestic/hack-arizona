import pytest

from spraywait.nozzles import ASABE_TO_DROPLET, LocalNozzleDB, Nozzle
from spraywait.pesticides import DEFAULT_PESTICIDE
from spraywait.spray_setup import SpraySetup, apply_nozzle


def test_every_catalog_nozzle_has_known_class():
    """All nozzles in nozzles.json use an ASABE class the mapper understands."""
    db = LocalNozzleDB()
    assert db.list()
    for name in db.list():
        assert db.get(name).asabe_class in ASABE_TO_DROPLET


@pytest.mark.parametrize("asabe,expected", [("very fine", "fine"), ("medium", "medium"), ("extremely coarse", "coarse")])
def test_droplet_size_mapping(asabe, expected):
    """ASABE classes collapse to the engine's fine/medium/coarse."""
    assert Nozzle("x", asabe).droplet_size == expected


def test_nozzle_lookup_case_insensitive_and_unknown():
    """Nozzle lookup ignores case and raises KeyError for unknown names."""
    db = LocalNozzleDB()
    assert db.get("disc-core HOLLOW cone").name == "Disc-core hollow cone"
    with pytest.raises(KeyError):
        db.get("nope")


def test_apply_nozzle_overrides_spray_fields_only():
    """The nozzle sets droplet size, VMD, and pressure; label limits stay from the pesticide."""
    p = SpraySetup().pesticides.get("Horticultural Oil")
    out = apply_nozzle(p, Nozzle("Fine tip", "fine", 150, 150))
    assert (out.droplet_size, out.nozzle, out.vmd_microns, out.pressure_psi) == ("fine", "Fine tip", 150, 150)
    assert out.max_temp_f == p.max_temp_f and p.droplet_size == "coarse"


def test_apply_nozzle_none_is_identity():
    """Without a nozzle the pesticide is returned unchanged."""
    assert apply_nozzle(DEFAULT_PESTICIDE, None) is DEFAULT_PESTICIDE


@pytest.mark.parametrize("name", [None, "", "generic (label defaults)"])
def test_resolve_default_pesticide(name):
    """Missing or generic pesticide names resolve to the label defaults."""
    assert SpraySetup().resolve(name, None).name == DEFAULT_PESTICIDE.name


def test_resolve_combines_pesticide_and_nozzle():
    """resolve() looks up both by name and merges them."""
    out = SpraySetup().resolve("captan", "Air-induction flat fan")
    assert out.name == "Captan" and out.droplet_size == "coarse" and out.nozzle == "Air-induction flat fan"
