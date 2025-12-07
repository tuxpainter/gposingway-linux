from pathlib import Path
import subprocess

from .constants import WORKDIR, GPOSINGWAY_PRESETS, GPOSINGWAY_SHADERS, USER_PRESETS, USER_SHADERS

SYMLINK_BASE: Path = WORKDIR / "symlink-farms"
PRESETS_SYMLINK_FARM: Path = SYMLINK_BASE / "presets"
SHADERS_SYMLINK_FARM: Path = SYMLINK_BASE / "shaders"

def _call_gardener(farm: Path, args: list[str]):
    # If Gardener exposed an API, we could do this trivially. It wants to be
    # called via CLI-only, though, so, we'll deal with it.
    gardener_args = ['gardener']
    for arg in args:
        gardener_args.append(arg)
    subprocess.run(
        gardener_args,
        capture_output=True,
        check=True,
        cwd=farm
    )



def _get_config_path(farm: Path) -> Path:
    return farm / ".symlink-garden" / "manifest.json"

def _initialize_single_farm(farm: Path, baseline_source: Path, user_source: Path):
    farm.mkdir(exist_ok=True, parents=True)
    if not (_get_config_path(farm)).exists():
        _call_gardener(farm, ['prepare'])
        _call_gardener(farm, ['plant', f'baseline:{baseline_source}'])
        _call_gardener(farm, ['plant', f'user:{user_source}'])


def _cultivate_single_farm(farm: Path):
    # This would be way easier if there was an auto-cultivate function. Alas.

    # I _think_ this lets us get away with not needing to read Gardener's
    # internal state.
    unowned_paths = [x for x in list(farm.glob('**/*')) if x.is_file(follow_symlinks=False)]
    for p in unowned_paths:
        if p.parent.name == '.symlink-garden':
            continue
        print(f"Preserving {p.name}")
        _call_gardener(farm, ['cultivate', '--package', 'user', p.resolve()])

    # TODO Manage empty directories


def refresh_symlink_farm():

    _initialize_single_farm(PRESETS_SYMLINK_FARM, GPOSINGWAY_PRESETS, USER_PRESETS)
    _initialize_single_farm(SHADERS_SYMLINK_FARM, GPOSINGWAY_SHADERS, USER_SHADERS)

    for farm in (PRESETS_SYMLINK_FARM, SHADERS_SYMLINK_FARM):
        _cultivate_single_farm(farm)
        _call_gardener(farm, ['tend'])
