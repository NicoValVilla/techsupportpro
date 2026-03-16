"""
Punto de entrada — TechSupport Pro CLI.

Uso:
    python cli.py --help
    python cli.py registrar
    python cli.py login
    python cli.py tickets
    python cli.py crear
    python cli.py alquileres
    python cli.py dashboard
    python cli.py cargar-csv clientes.csv

Variable de entorno:
    MODO_REPO : memoria | postgres | json  (default: memoria)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from techsupportpro.config import Contenedor
from techsupportpro.infrastructure.adapters_in.cli import crear_cli

contenedor = Contenedor.crear()
cli = crear_cli(contenedor)

if __name__ == "__main__":
    cli()
