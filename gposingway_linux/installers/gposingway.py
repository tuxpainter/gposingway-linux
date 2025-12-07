import subprocess

from gposingway_linux.constants import GPOSINGWAY_DIR

def install():
    "Installs or updates GPosingway in our workdir."
    if not (GPOSINGWAY_DIR / '.git').exists():
        print("Downloading GPosingway...")
        subprocess.run(['git', 'clone', 'https://github.com/gposingway/gposingway.git', GPOSINGWAY_DIR],
            capture_output=True,
            check=True)
        print("GPosingway downloaded.")
    else:
        print("Getting updates for the ReShade installer...")
        subprocess.run(
            ['git', 'pull', '--rebase'],
            capture_output=True,
            check=True,
            cwd=GPOSINGWAY_DIR
        )
        print("GPosingway updated.")

    # TODO run git tag and checkout the latest (instead of living on head)
