from pathlib import Path
from xdg_base_dirs import xdg_data_home

FFXIV_STEAM_APP_ID = 39210

FFXIV_PATH_ENV = 'FFXIV_PATH'
WINE_PREFIX_ENV = 'WINE_PREFIX'

############
#   DIRS   #
############
WORKDIR:Path = xdg_data_home() / 'gposingway_linux'

GPOSINGWAY_DIR: Path = WORKDIR / 'gposingway'
GPOSINGWAY_PRESETS: Path = GPOSINGWAY_DIR / 'reshade-presets'
GPOSINGWAY_SHADERS: Path = GPOSINGWAY_DIR / 'reshade-shaders'

USER_PRESETS: Path = WORKDIR / 'user-presets'
USER_SHADERS: Path = WORKDIR / 'user-shaders'

FFXIV_PRESETS_DIR = 'reshade-presets'
FFXIV_SHADERS_DIR ='reshade-shaders'
FFXIV_RESHADE_INI = 'ReShade.ini'
FFXIV_RESHADE_PRESETS_INI = 'ReShadePreset.ini'


def ensure_dirs():
    WORKDIR.mkdir(exist_ok=True)
    print(f"Using {str(WORKDIR)} as our working directory.")

    USER_PRESETS.mkdir(exist_ok=True)
    USER_SHADERS.mkdir(exist_ok=True)
