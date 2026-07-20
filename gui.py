from pathlib import Path
import subprocess
import sys


def run_gui():

    app = Path(__file__).parent / "ui" / "app.py"
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app),
            ]
        )
    except KeyboardInterrupt:
        pass    