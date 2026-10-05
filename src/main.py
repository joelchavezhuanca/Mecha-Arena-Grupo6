"""
Punto de entrada principal de Mecha-Arena.

Uso:
    python main.py
"""

from src.ui.cli_interface import CLIInterface


def main() -> None:
    cli = CLIInterface()
    cli.ejecutar()


if __name__ == "__main__":
    main()
