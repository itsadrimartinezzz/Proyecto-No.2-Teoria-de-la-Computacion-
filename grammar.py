from pathlib import Path


def load_grammar(path):
    # Lee las reglas del archivo e identifica el simbolo inicial
    grammar = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("->") != 1:
            raise ValueError(f"Linea {number}: usa una flecha -> por regla.")
        head, body = line.split("->")
        head = head.strip()
        if not head or len(head.split()) != 1:
            raise ValueError(f"Linea {number}: el lado izquierdo debe ser una variable.")
        grammar.setdefault(head, set())
        for option in body.split("|"):
            symbols = option.split()
            if not symbols:
                raise ValueError(f"Linea {number}: escribe e para una produccion vacia.")
            if any(symbol in {"e", "epsilon", "ε"} for symbol in symbols):
                if len(symbols) != 1:
                    raise ValueError(f"Linea {number}: epsilon debe aparecer sola.")
                symbols = []
            grammar[head].add(tuple(symbols))
    if not grammar:
        raise ValueError("El archivo no contiene reglas.")
    return grammar, next(iter(grammar))


def fresh_name(grammar, prefix, extra_names=()):
    # Evita repetir nombres de variables o terminales existentes
    used = set(grammar)
    used.update(extra_names)
    for bodies in grammar.values():
        for body in bodies:
            used.update(body)
    number = 0
    while f"{prefix}{number}" in used:
        number += 1
    return f"{prefix}{number}"


def remove_empty(grammar, start):
    # Elimina reglas vacias y conserva epsilon en el inicio cuando corresponde
    nullable = set()
    changed = True
    while changed:
        changed = False
        for head, bodies in grammar.items():
            if head not in nullable and any(all(s in nullable for s in body) for body in bodies):
                nullable.add(head)
                changed = True

    result = {head: set() for head in grammar}
    for head, bodies in grammar.items():
        for body in bodies:
            options = {()}
            for symbol in body:
                extended = {option + (symbol,) for option in options}
                if symbol in nullable:
                    extended.update(options)
                options = extended
            result[head].update(option for option in options if option)
    if start in nullable:
        result[start].add(())
    return result


def remove_unit(grammar):
    # Sigue las reglas A -> B y copia las producciones finales de B en A
    result = {head: set() for head in grammar}
    for head in grammar:
        reached = {head}
        pending = [head]
        while pending:
            current = pending.pop()
            for body in sorted(grammar[current]):
                if len(body) == 1 and body[0] in grammar:
                    if body[0] not in reached:
                        reached.add(body[0])
                        pending.append(body[0])
                else:
                    result[head].add(body)
    return result


def remove_useless(grammar, start):
    # Elimina variables que no generan palabras o no se alcanzan desde el inicio
    productive = set()
    changed = True
    while changed:
        changed = False
        for head, bodies in grammar.items():
            if head in productive:
                continue
            for body in bodies:
                if all(s not in grammar or s in productive for s in body):
                    productive.add(head)
                    changed = True
                    break

    # Conserva las claves para no confundir variables inutiles con terminales
    filtered = {head: set() for head in grammar}
    for head in productive:
        filtered[head] = {
            body for body in grammar[head]
            if all(s not in grammar or s in productive for s in body)
        }
    reached = {start}
    pending = [start]
    while pending:
        for body in filtered[pending.pop()]:
            for symbol in body:
                if symbol in grammar and symbol not in reached:
                    reached.add(symbol)
                    pending.append(symbol)
    return {head: filtered[head] for head in grammar if head in reached}


def replace_terminals(grammar):
    # En cuerpos de dos o mas simbolos, cada terminal recibe una variable auxiliar
    result = {head: set() for head in grammar}
    aliases = {}
    for head, bodies in grammar.items():
        for body in sorted(bodies):
            updated = []
            for symbol in body:
                if len(body) > 1 and symbol not in grammar:
                    if symbol not in aliases:
                        name = fresh_name(grammar, "TERM", result)
                        aliases[symbol] = name
                        result[name] = {(symbol,)}
                    symbol = aliases[symbol]
                updated.append(symbol)
            result[head].add(tuple(updated))
    return result


def split_long_rules(grammar):
    # Divide cada cuerpo largo en una cadena de pares
    result = {head: set() for head in grammar}
    for head, bodies in grammar.items():
        for body in sorted(bodies):
            current = head
            remaining = body
            while len(remaining) > 2:
                name = fresh_name(grammar, "PAIR", result)
                result[current].add((remaining[0], name))
                result[name] = set()
                current = name
                remaining = remaining[1:]
            result[current].add(remaining)
    return result


def is_cnf(grammar, start):
    # Comprueba que todas las reglas respeten la Forma Normal de Chomsky
    for head, bodies in grammar.items():
        for body in bodies:
            if start in body:
                return False
            if not body and head == start:
                continue
            if len(body) == 1 and body[0] not in grammar:
                continue
            if len(body) == 2 and all(s in grammar for s in body):
                continue
            return False
    return True


def to_cnf(grammar, start):
    # Convierte la gramatica a CNF y guarda cada etapa del proceso
    steps = [("Gramatica original", grammar)]
    # Un inicio nuevo permite conservar epsilon sin dejarlo en otros cuerpos
    if any(start in body for bodies in grammar.values() for body in bodies):
        new_start = fresh_name(grammar, "START")
        grammar = {new_start: {(start,)}, **grammar}
        start = new_start
        steps.append(("Proteger simbolo inicial", grammar))
    grammar = remove_empty(grammar, start)
    steps.append(("Eliminar producciones vacias", grammar))
    grammar = remove_unit(grammar)
    steps.append(("Eliminar producciones unitarias", grammar))
    grammar = remove_useless(grammar, start)
    steps.append(("Eliminar simbolos inutiles", grammar))
    grammar = replace_terminals(grammar)
    steps.append(("Separar terminales", grammar))
    grammar = split_long_rules(grammar)
    steps.append(("Dividir reglas largas: CNF final", grammar))
    return grammar, start, steps


def format_grammar(grammar):
    # Prepara las reglas como texto con las flechas alineadas
    lines = []
    width = max(len(head) for head in grammar)  # Alinea las flechas al imprimir
    for head, bodies in grammar.items():
        options = [" ".join(body) if body else "e" for body in sorted(bodies)]
        lines.append(f"  {head:<{width}} -> {' | '.join(options) if options else '(sin producciones)'}")
    return "\n".join(lines)
