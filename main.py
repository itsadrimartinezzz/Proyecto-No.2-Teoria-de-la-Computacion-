import argparse
from pathlib import Path
from time import perf_counter

from cyk import format_table, format_tree, parse
from grammar import format_grammar, is_cnf, load_grammar, to_cnf


LINE = "-" * 60


def get_terminals(grammar):
    # Obtiene los terminales de la gramatica sin repetirlos
    return sorted({s for bodies in grammar.values() for body in bodies for s in body if s not in grammar})


def read_tokens(sentence, grammar):
    # Separa la frase y ajusta mayusculas y puntos si el simbolo no es un terminal
    terminals = set(get_terminals(grammar))
    tokens = []
    for token in sentence.split():
        if token not in terminals:
            token = token.lower().rstrip(".")
        if token:
            tokens.append(token)
    return tokens


def print_title(text):
    # Muestra un titulo entre separadores
    print(f"\n{LINE}\n  {text}\n{LINE}")


def print_instructions():
    # Explica como ingresar frases y terminar el programa
    print_title("COMO USARLO")
    print("  1. Escribe una frase con las palabras separadas por espacios.")
    print("  2. Presiona Enter para saber si pertenece al lenguaje.")
    print("  3. Escribe 'salir' para terminar.")


def check_sentence(sentence, grammar, start, show_table):
    # Valida una frase y muestra el resultado, el tiempo y el arbol de analisis
    tokens = read_tokens(sentence, grammar)
    begin = perf_counter()
    accepted, table, tree = parse(tokens, grammar, start)
    elapsed = (perf_counter() - begin) * 1000

    print(LINE)
    print(f"  Frase:      {' '.join(tokens) or '(cadena vacia)'}")
    print(f"  Resultado:  {'SÍ pertenece al lenguaje' if accepted else 'NO pertenece al lenguaje'}")
    print(f"  Tiempo CYK: {elapsed:.6f} ms")
    print(LINE)
    if show_table:
        print(f"\nTabla CYK:\n{format_table(tokens, table)}")
    if tree:
        print(f"\nArbol de analisis (CNF):\n{format_tree(tree)}")
    else:
        print("  No existe un arbol de analisis para esta entrada.")


def main():
    # Carga la gramatica y coordina la validacion de las frases
    parser = argparse.ArgumentParser(description="Convierte una CFG a CNF y aplica CYK.")
    parser.add_argument("--grammar", default=str(Path(__file__).parent / "grammars" / "english.txt"))
    parser.add_argument("--sentence", help="Frase con los simbolos separados por espacios.")
    parser.add_argument("--steps", action="store_true", help="Muestra los pasos de conversion.")
    parser.add_argument("--table", action="store_true", help="Muestra los intervalos de la tabla CYK.")
    args = parser.parse_args()

    try:
        grammar, start = load_grammar(args.grammar)
        grammar, start, steps = to_cnf(grammar, start)
        if not is_cnf(grammar, start):
            raise ValueError("La conversion no produjo una gramatica en CNF.")

        print_title("PROYECTO 2")
        print(f"  Gramatica: {Path(args.grammar).name}")
        print(f"  Inicio:    {start}")
        if args.steps:
            for title, rules in steps:
                print(f"\n{title}:\n{format_grammar(rules)}")
        else:
            print(f"\nGramatica en CNF:\n{format_grammar(grammar)}")

        if args.sentence is not None:
            print()
            check_sentence(args.sentence, grammar, start, args.table)
            return

        print_instructions()
        while True:
            sentence = input("\nFrase > ").replace("﻿", "")  # Quita el BOM que agrega PowerShell
            if sentence.strip().lower() == "salir":
                print("Programa terminado.")
                break
            check_sentence(sentence, grammar, start, args.table)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nEntrada cancelada.\n")


if __name__ == "__main__":
    main()
