"""Interfaz de línea de comandos del experimento AMPS por recencia."""
import argparse
from pathlib import Path
from mediaamps.validation import run

def main():
    parser = argparse.ArgumentParser(description='Validación de cobertura por recencia con AMPS 2011')
    parser.add_argument('--data-dir', type=Path, default=Path('data/amps'))
    parser.add_argument('--output', type=Path, default=Path('nueva_validacion.csv'))
    parser.add_argument('--bootstrap', type=int, default=0, help='Remuestras pareadas de personas de evaluación')
    parser.add_argument('--bootstrap-output', type=Path, default=Path('nuevo_bootstrap.csv'))
    args = parser.parse_args()
    if args.bootstrap < 0:
        parser.error('--bootstrap debe ser no negativo')
    run(args.data_dir, args.output, args.bootstrap, args.bootstrap_output)

if __name__ == '__main__':
    main()
