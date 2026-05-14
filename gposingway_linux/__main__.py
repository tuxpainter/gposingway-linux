import argparse
from configparser import ConfigParser, UNNAMED_SECTION
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import vdf

from gposingway_linux.constants import *
from gposingway_linux.installers import install_gpway, install_reshade
from gposingway_linux.symlink_mgr import refresh_symlink_farm, PRESETS_SYMLINK_FARM, SHADERS_SYMLINK_FARM


# Shared file/directory lists used by both install and uninstall paths.
RESHADE_GAME_FILES = ['dxgi.dll', D3D_COMPILER_DLL, FFXIV_RESHADE_INI, FFXIV_RESHADE_PRESETS_INI]
GAME_SYMLINK_DIRS = [
    (FFXIV_PRESETS_DIR, PRESETS_SYMLINK_FARM),
    (FFXIV_SHADERS_DIR, SHADERS_SYMLINK_FARM),
]


class EnvInfo:
    def __init__(self):
        self.method = 'Environment'
        self.ffxiv_path_raw = os.getenv(FFXIV_PATH_ENV, None)
        self.wine_prefix_raw = os.getenv(WINE_PREFIX_ENV, None)
        self.valid = self.ffxiv_path_raw is not None and self.wine_prefix_raw is not None

    @property
    def ffxiv_path(self) -> Path:
        return Path(self.ffxiv_path_raw)

    @property
    def wine_prefix(self) -> Path:
        return Path(self.wine_prefix_raw)


class XLCoreInfo:
    def __init__(self):
        self.method = 'XLCore'
        self.ffxiv_path = None
        self.wine_prefix = None
        self.valid = False
        try:
            xlcore_path = Path.home() / '.xlcore'
            launcher_ini_path = xlcore_path / 'launcher.ini'
            launcher_config = ConfigParser(allow_unnamed_section=True, strict=False)
            launcher_config.read(launcher_ini_path)
            self.ffxiv_path = Path(launcher_config[UNNAMED_SECTION]['GamePath'])
            self.wine_prefix = xlcore_path / 'wineprefix'
            self.valid = True
        except KeyError:
            pass


class SteamInfo:
    def __find_ffxiv() -> list[Path]:
        with open(Path.home() / '.steam' / 'steam' / 'config'/ 'libraryfolders.vdf') as libvdf:
            libraries = vdf.load(libvdf)
        libs = []
        for lib in libraries['libraryfolders'].values():
            path = Path(lib['path'])
            if path.is_dir():
                libs.append(path)

        return next((x for x in libs if (x/'steamapps'/'appmanifest_39210.acf').exists()), None)


    def __init__(self):
        self.method = 'Steam'
        ffxiv_lib = SteamInfo.__find_ffxiv()
        if ffxiv_lib:
            steamapp_path = ffxiv_lib / 'steamapps'
            self.ffxiv_path = steamapp_path / 'common' / 'FINAL FANTASY XIV Online'
            self.wine_prefix = steamapp_path / 'compatdata' / str(FFXIV_STEAM_APP_ID) / 'pfx'
            self.valid = True
        else:
            self.ffxiv_path = self.wine_prefix = None
            self.valid = False


class LutrisInfo:
    pass

@dataclass
class ManualInfo:
    def __init__(self):
        pass

    @property
    def ffxiv_path(self) -> Path:
        # TODO Input and validation loop
        pass

    @property
    def wine_prefix(self) -> Path:
        # TODO Input and validation loop
        pass


def detect_ffxiv():
    """Detect FFXIV install and return the info object, or None."""
    infoset = [EnvInfo(), XLCoreInfo(), SteamInfo()]
    info = next((x for x in infoset if x.valid), None)
    if info is None:
        print("Could not detect your FFXIV installation.")
        print("Set the FFXIV_PATH and WINE_PREFIX environment variables and try again.")
        exit(1)
    return info


# ---------------------------------------------------------------------------
#  Unified install / uninstall logic
# ---------------------------------------------------------------------------

def _run_install(info, dry_run=False):
    """Shared install logic for both dry-run preview and actual install."""
    if not dry_run:
        if not shutil.which('git'):
            print("`git` not found on your path. Please install it and ensure it is accessible. Exiting.")
            exit(-1)
        ensure_dirs()

    ffxiv_path = info.ffxiv_path / 'game'
    sys32 = info.wine_prefix / 'drive_c' / 'windows' / 'system32'
    reshade_installer_dir = WORKDIR / 'reshade-installer'

    # Paths used for config backup/restore
    reshade_ini = ffxiv_path / FFXIV_RESHADE_INI
    reshade_presets_ini = ffxiv_path / FFXIV_RESHADE_PRESETS_INI

    # --- ReShade installer ---
    if (reshade_installer_dir / '.git').exists():
        print(f"  [update] git pull reshade-steam-proton at {reshade_installer_dir}")
    else:
        print(f"  [clone]  git clone reshade-steam-proton to {reshade_installer_dir}")

    print(f"  [run]    reshade-linux.sh against {ffxiv_path}")
    print(f"  [copy]   {D3D_COMPILER_DLL} -> {sys32 / D3D_COMPILER_DLL}")

    current_d3d = sys32 / D3D_COMPILER_DLL
    backup_d3d = sys32 / D3D_COMPILER_BACKUP
    if current_d3d.exists() and not backup_d3d.exists():
        print(f"  [backup] {current_d3d} -> {D3D_COMPILER_BACKUP}")

    if not dry_run:
        # Back up existing configs before the reshade installer can overwrite them
        uuid = uuid4()
        reshade_ini_bak = ffxiv_path / (FFXIV_RESHADE_INI + f'.bak.{uuid}')
        reshade_presets_ini_bak = ffxiv_path / (FFXIV_RESHADE_PRESETS_INI + f'.bak.{uuid}')
        if reshade_ini.exists():
            shutil.copy(reshade_ini, reshade_ini_bak)
        if reshade_presets_ini.exists():
            shutil.copy(reshade_presets_ini, reshade_presets_ini_bak)

        install_reshade(ffxiv_path, wine_prefix=info.wine_prefix)

    # --- GPosingway ---
    if (GPOSINGWAY_DIR / '.git').exists():
        print(f"  [update] git pull GPosingway at {GPOSINGWAY_DIR}")
    else:
        print(f"  [clone]  git clone GPosingway to {GPOSINGWAY_DIR}")

    if not dry_run:
        install_gpway()

    # --- Symlink farms ---
    print(f"  [setup]  symlink farms at {WORKDIR / 'symlink-farms'}")

    if not dry_run:
        refresh_symlink_farm()

    for dir_name, farm_target in GAME_SYMLINK_DIRS:
        link_path = ffxiv_path / dir_name
        if not link_path.exists():
            print(f"  [link]   {link_path} -> {farm_target}")
            if not dry_run:
                link_path.symlink_to(farm_target)
        else:
            print(f"  [skip]   {link_path} already exists")

    # --- Configs ---
    if reshade_ini.exists():
        print(f"  [keep]   {reshade_ini} (backup and restore)")
    else:
        print(f"  [create] {reshade_ini} (from GPosingway defaults)")

    if reshade_presets_ini.exists():
        print(f"  [keep]   {reshade_presets_ini} (backup and restore)")
    else:
        print(f"  [create] {reshade_presets_ini} (from GPosingway defaults)")

    if not dry_run:
        if reshade_ini_bak.exists():
            shutil.copy(reshade_ini_bak, reshade_ini)
            reshade_ini_bak.unlink()
            print("Restored existing ReShade.ini")
        else:
            shutil.copy(GPOSINGWAY_DIR / FFXIV_RESHADE_INI, reshade_ini)
            print("Bootstrapped with GPosingway default ReShade.ini")

        if reshade_presets_ini_bak.exists():
            shutil.copy(reshade_presets_ini_bak, reshade_presets_ini)
            reshade_presets_ini_bak.unlink()
            print("Restored existing ReShadePresets.ini")
        else:
            shutil.copy(GPOSINGWAY_DIR / FFXIV_RESHADE_PRESETS_INI, reshade_presets_ini)
            print("Bootstrapped with GPosingway default ReShadePreset.ini")

        print("All done!")

        if info.method == 'Steam':
            print("You may need to set the following launch arguments for FFXIV in Steam: `WINEDLLOVERRIDES=\"d3dcompiler_47=n;dxgi=n,b\" %command%`")


def _run_uninstall(info, dry_run=False):
    """Shared uninstall logic for both dry-run preview and actual uninstall."""
    ffxiv_path = info.ffxiv_path / 'game'
    sys32 = info.wine_prefix / 'drive_c' / 'windows' / 'system32'

    if not dry_run:
        print(f"Uninstalling ReShade/GPosingway from {ffxiv_path}...\n")

    # --- Symlinks (remove first since they point into our workdir) ---
    for dir_name, _ in GAME_SYMLINK_DIRS:
        target = ffxiv_path / dir_name
        if target.is_symlink():
            print(f"  [unlink] {target} -> {target.resolve()}")
            if not dry_run:
                target.unlink()
        elif target.exists():
            print(f"  [warn]   {target} exists but is not a symlink, {'skipping' if not dry_run else 'would skip'}")
        else:
            print(f"  [skip]   {target} (not present)")

    # --- ReShade files from game dir ---
    for name in RESHADE_GAME_FILES:
        f = ffxiv_path / name
        if f.exists():
            print(f"  [remove] {f}")
            if not dry_run:
                f.unlink()
        else:
            print(f"  [skip]   {f} (not present)")

    # --- d3dcompiler backup in system32 ---
    backup = sys32 / D3D_COMPILER_BACKUP
    current = sys32 / D3D_COMPILER_DLL
    if backup.exists():
        print(f"  [restore] {backup} -> {current}")
        if not dry_run:
            if current.exists():
                current.unlink()
            backup.rename(current)
    else:
        print(f"  [skip]   {current} (no backup to restore from, leaving alone)")

    # --- Working directory ---
    if WORKDIR.exists():
        print(f"  [remove] {WORKDIR} (entire working directory)")
        if not dry_run:
            shutil.rmtree(WORKDIR)
    else:
        print(f"  [skip]   {WORKDIR} (not present)")

    if not dry_run:
        print("\nUninstall complete.")


# ---------------------------------------------------------------------------
#  Public action handlers (thin wrappers)
# ---------------------------------------------------------------------------

def do_dry_run(info):
    """Show what install/uninstall would do without changing anything."""
    print("\n--- Dry Run: Install would do the following ---\n")
    _run_install(info, dry_run=True)
    print("\n--- Dry Run: Uninstall would do the following ---\n")
    _run_uninstall(info, dry_run=True)
    print("\nRun with 'install' or 'uninstall' to perform these actions.")


def do_install(info):
    """Run the full install flow."""
    _run_install(info, dry_run=False)


def do_uninstall(info):
    """Remove ReShade and GPosingway from the FFXIV install."""
    _run_uninstall(info, dry_run=False)


def main():
    parser = argparse.ArgumentParser(
        prog='gposingway-linux',
        description='Install ReShade and GPosingway shaders/presets for FFXIV on Linux.'
    )
    parser.add_argument(
        'action',
        nargs='?',
        default='dry-run',
        choices=['dry-run', 'install', 'uninstall'],
        help="Action to perform (default: dry-run)"
    )
    args = parser.parse_args()

    info = detect_ffxiv()

    print(f"Found the following FFXIV install information via {info.method}")
    print(f"\tGame location:\t{info.ffxiv_path}")
    print(f"\tWine prefix:\t{info.wine_prefix}")

    match args.action:
        case 'dry-run':
            do_dry_run(info)
        case 'install':
            do_install(info)
        case 'uninstall':
            do_uninstall(info)

if __name__ == '__main__':
    main()
