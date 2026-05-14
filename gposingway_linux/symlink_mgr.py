from collections import OrderedDict
from pathlib import Path

from gardener import Garden, Package, simple_run

from .constants import WORKDIR, GPOSINGWAY_PRESETS, GPOSINGWAY_SHADERS, USER_PRESETS, USER_SHADERS

SYMLINK_BASE: Path = WORKDIR / "symlink-farms"
PRESETS_SYMLINK_FARM: Path = SYMLINK_BASE / "presets"
SHADERS_SYMLINK_FARM: Path = SYMLINK_BASE / "shaders"


def _get_config_path(farm: Path) -> Path:
    return farm / ".symlink-garden" / "manifest.json"

def _initialize_single_farm(farm: Path, baseline_source: Path, user_source: Path):
    farm.mkdir(exist_ok=True, parents=True)
    if not (_get_config_path(farm)).exists():
        garden = Garden(farm)
        simple_run(garden.prepare())
        simple_run(garden.plant(OrderedDict({
            "baseline": Package("baseline", baseline_source),
            "user": Package("user", user_source),
        })))


def _cultivate_single_farm(farm: Path):
    garden = Garden(farm)

    unowned_paths = [x for x in list(farm.glob('**/*')) if x.is_file(follow_symlinks=False)]
    for p in unowned_paths:
        if p.parent.name == '.symlink-garden':
            continue
        print(f"Preserving {p.name}")
        simple_run(garden.cultivate("user", [p.resolve()]))

    # TODO Manage empty directories


def refresh_symlink_farm():

    _initialize_single_farm(PRESETS_SYMLINK_FARM, GPOSINGWAY_PRESETS, USER_PRESETS)
    _initialize_single_farm(SHADERS_SYMLINK_FARM, GPOSINGWAY_SHADERS, USER_SHADERS)

    for farm in (PRESETS_SYMLINK_FARM, SHADERS_SYMLINK_FARM):
        _cultivate_single_farm(farm)
        garden = Garden(farm)
        simple_run(garden.tend())
