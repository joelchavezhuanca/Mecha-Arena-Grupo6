import os
import sys

# Asegurar que el directorio raíz esté en sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configurar UTF-8 en consola de Windows para evitar errores con caracteres especiales y emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.ui.cli_interface import CLIInterface


def main() -> None:
    cli = CLIInterface()
    cli.ejecutar()


if __name__ == "__main__":
    main()
