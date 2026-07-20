from gui import run_gui
from cli import run_cli
import argparse

def main():

    parser = argparse.ArgumentParser(
        description="Simulador de Transmisión Digital"
    )

    parser.add_argument(
        "-m",
        "--mode",
        choices=["gui", "cli"],
        default="cli",
        help="Modo de ejecución"
    )

    args = parser.parse_args()

    if args.mode == "gui":
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()