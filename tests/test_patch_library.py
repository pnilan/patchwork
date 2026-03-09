import time

import pytest

from patchwork.patch_library import PatchLibrary


@pytest.fixture
def patch_lib(tmp_path):
    with PatchLibrary(db_path=tmp_path / "test.db") as lib:
        yield lib


def test_save_and_get(patch_lib):
    patch = patch_lib.save(
        name="dark-bass",
        synth="minitaur",
        settings={"cutoff": 45, "resonance": 80},
        description="A dark bass patch",
    )
    assert patch.name == "dark-bass"
    assert patch.synth == "minitaur"
    assert patch.settings == {"cutoff": 45, "resonance": 80}
    assert patch.description == "A dark bass patch"

    loaded = patch_lib.get("dark-bass")
    assert loaded is not None
    assert loaded.name == patch.name
    assert loaded.synth == patch.synth
    assert loaded.settings == patch.settings
    assert loaded.description == patch.description


def test_save_overwrites_existing(patch_lib):
    patch1 = patch_lib.save(
        name="bass",
        synth="minitaur",
        settings={"cutoff": 45},
    )
    time.sleep(0.01)
    patch2 = patch_lib.save(
        name="bass",
        synth="minitaur",
        settings={"cutoff": 90, "resonance": 50},
        description="updated",
    )
    assert patch2.name == "bass"
    assert patch2.settings == {"cutoff": 90, "resonance": 50}
    assert patch2.description == "updated"
    assert patch2.updated_at > patch1.updated_at


def test_get_nonexistent(patch_lib):
    assert patch_lib.get("nonexistent") is None


def test_list_all(patch_lib):
    patch_lib.save(name="a", synth="minitaur", settings={"cutoff": 10})
    time.sleep(0.01)
    patch_lib.save(name="b", synth="tb03", settings={"cutoff": 20})
    time.sleep(0.01)
    patch_lib.save(name="c", synth="minitaur", settings={"cutoff": 30})

    patches = patch_lib.list()
    assert len(patches) == 3
    # Most recently updated first
    assert patches[0].name == "c"
    assert patches[1].name == "b"
    assert patches[2].name == "a"


def test_list_filtered_by_synth(patch_lib):
    patch_lib.save(name="a", synth="minitaur", settings={"cutoff": 10})
    patch_lib.save(name="b", synth="tb03", settings={"cutoff": 20})
    patch_lib.save(name="c", synth="minitaur", settings={"cutoff": 30})

    patches = patch_lib.list(synth="minitaur")
    assert len(patches) == 2
    names = {p.name for p in patches}
    assert names == {"a", "c"}


def test_list_filtered_case_insensitive(patch_lib):
    patch_lib.save(name="a", synth="minitaur", settings={"cutoff": 10})
    patch_lib.save(name="b", synth="tb03", settings={"cutoff": 20})

    patches = patch_lib.list(synth="MINITAUR")
    assert len(patches) == 1
    assert patches[0].name == "a"


def test_list_empty(patch_lib):
    assert patch_lib.list() == []


def test_delete_existing(patch_lib):
    patch_lib.save(name="bass", synth="minitaur", settings={"cutoff": 45})
    assert patch_lib.delete("bass") is True
    assert patch_lib.get("bass") is None


def test_delete_nonexistent(patch_lib):
    assert patch_lib.delete("nonexistent") is False


def test_settings_roundtrip(patch_lib):
    settings = {
        "cutoff": 45,
        "resonance": 80,
        "osc_mix": 100,
        "lfo_rate": 0,
        "volume": 127,
    }
    patch_lib.save(name="complex", synth="minitaur", settings=settings)
    loaded = patch_lib.get("complex")
    assert loaded is not None
    assert loaded.settings == settings


def test_open_creates_directory(tmp_path):
    db_path = tmp_path / "subdir" / "nested" / "test.db"
    lib = PatchLibrary(db_path=db_path)
    lib.open()
    try:
        assert db_path.parent.exists()
    finally:
        lib.close()


def test_description_none(patch_lib):
    patch_lib.save(name="nodesc", synth="minitaur", settings={"cutoff": 10}, description=None)
    loaded = patch_lib.get("nodesc")
    assert loaded is not None
    assert loaded.description is None


def test_operations_after_close(tmp_path):
    lib = PatchLibrary(db_path=tmp_path / "test.db")
    lib.open()
    lib.close()
    with pytest.raises(RuntimeError, match="Database not open"):
        lib.save(name="test", synth="minitaur", settings={"cutoff": 50})


def test_context_manager(tmp_path):
    db_path = tmp_path / "ctx.db"
    with PatchLibrary(db_path=db_path) as lib:
        lib.save(name="test", synth="minitaur", settings={"cutoff": 50})
        loaded = lib.get("test")
        assert loaded is not None
        assert loaded.settings == {"cutoff": 50}
    # After exiting, connection should be closed
    assert lib._conn is None
