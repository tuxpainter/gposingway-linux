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


def main():
    # Check pre-reqs
    if not shutil.which('git'):
        print("`git` not found on your path. Please install it and ensure it is accessible. Exiting.")
        exit(-1)

    # Initialize our workspace
    ensure_dirs()

    # Gather information
    infoset = [EnvInfo(), XLCoreInfo(), SteamInfo()]
    info = next(x for x in infoset if x.valid)

    print(f"Found the following FFXIV install information via {info.method}")
    print(f"\tGame location:\t{info.ffxiv_path}")
    print(f"\tWine prefix:\t{info.wine_prefix}")

    ffxiv_path = info.ffxiv_path / 'game'

    uuid = uuid4()
    reshade_ini: Path = ffxiv_path / FFXIV_RESHADE_INI
    reshade_ini_bak: Path = ffxiv_path / (FFXIV_RESHADE_INI + f'.bak.{uuid}')
    reshade_presets_ini: Path = ffxiv_path / FFXIV_RESHADE_PRESETS_INI
    reshade_presets_ini_bak: Path = ffxiv_path / (FFXIV_RESHADE_PRESETS_INI + f'.bak.{uuid}')

    if reshade_ini.exists():
        shutil.copy(reshade_ini, reshade_ini_bak)

    if reshade_presets_ini.exists():
        shutil.copy(reshade_presets_ini, reshade_presets_ini_bak)

    install_reshade(ffxiv_path, wine_prefix=info.wine_prefix)
    install_gpway()


    # Symlink farm nonsense now.
    refresh_symlink_farm()
    if not (ffxiv_path / FFXIV_PRESETS_DIR).exists():
        p_dir: Path = (ffxiv_path / FFXIV_PRESETS_DIR)
        print(f"Linking {p_dir} to {PRESETS_SYMLINK_FARM}")
        p_dir.symlink_to(PRESETS_SYMLINK_FARM)

    if not (ffxiv_path / FFXIV_SHADERS_DIR).exists():
        p_dir: Path = (ffxiv_path / FFXIV_SHADERS_DIR)
        print(f"Linking {p_dir} to {SHADERS_SYMLINK_FARM}")
        p_dir.symlink_to(SHADERS_SYMLINK_FARM)

    # Restore or bootstrap configs
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

if __name__ == '__main__':
    main()
