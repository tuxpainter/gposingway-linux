import os
from pathlib import Path
import shutil
import subprocess

from gposingway_linux.constants import WORKDIR

def install(ffxiv_path: Path, wine_prefix: Path):
    "Install ReShade using https://github.com/kevinlekiller/reshade-steam-proton"

    RESHADE_INSTALLER_DIR = WORKDIR / 'reshade-installer'
    RESHADE_INSTALLER_DIR.mkdir(exist_ok=True)
    RESHADE_DATA_DIR = WORKDIR / 'reshade'

    reshade_install_env = {
        'MAIN_PATH': str(RESHADE_DATA_DIR),
        'SHADER_REPOS': '',
        'RESHADE_ADDON_SUPPORT': '1'
    }

    # TODO Do we need to back up the user's ReShade.ini?

    for k in os.environ:
        reshade_install_env[k] = os.environ[k]

    if not (RESHADE_INSTALLER_DIR / '.git').exists():
        print("Downloading ReShade installer...")
        subprocess.run(['git', 'clone', 'https://github.com/kevinlekiller/reshade-steam-proton.git', RESHADE_INSTALLER_DIR],
            capture_output=True,
            check=True)
        print("ReShade installer downloaded.")
    else:
        # This tends not to update often, but rather safe than sorry...
        print("Getting updates for the ReShade installer...")
        subprocess.run(
            ['git', 'pull', '--rebase'],
            capture_output=True,
            check=True,
            cwd=RESHADE_INSTALLER_DIR
        )
        print("ReShade installer updated.")

    reshade_install_stdin = "\n".join(['i', str(ffxiv_path), 'y', 'n', '64', 'dxgi', 'y', ''])

    print(f"Installing ReShade for FFXIV at {ffxiv_path}...")
    subprocess.run(
        ['./reshade-linux.sh'],
        input=reshade_install_stdin,
        text=True,
        env=reshade_install_env,
        cwd=RESHADE_INSTALLER_DIR,
        capture_output=True
    )

    # reshade-linux.sh will tell the user to set WINEDLLOVERRIDES="d3dcompiler_47=n;dxgi=n,b"

    # Fix d3dcompiler_47.dll in Wine/Proton path

    sys32 = wine_prefix / 'drive_c' / 'windows' / 'system32'

    target_d3d:Path = sys32/'d3dcompiler_47.dll'
    if target_d3d.exists():
        print("Backing up current d3dcompiler_47.dll to d3dcompiler_47._dll. If a backup already exists here, it will be destroyed.")
        target_d3d.rename(sys32 / 'd3dcompiler_47._dll')

    print("Copying d3dcompiler_47.dll from Reshade into your Wine/Proton environment")
    shutil.copy(ffxiv_path / 'd3dcompiler_47.dll', target_d3d)

    (ffxiv_path / 'ReShade.ini').unlink()
    (ffxiv_path / 'ReShade_shaders').unlink()
