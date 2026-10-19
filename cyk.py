def build_indexes(grammar):
    # Agrupa reglas por su cuerpo para evitar recorrer toda la gramatica por celda
    terminal_rules = {}
    binary_rules = {}
    for head, bodies in grammar.items():
        for body in sorted(bodies):
            if len(body) == 1:
                terminal_rules.setdefault(body[0], []).append(head)
            elif len(body) == 2:
                binary_rules.setdefault(body, []).append(head)
    return terminal_rules, binary_rules


def parse(tokens, grammar, start):
    # Aplica CYK y devuelve el resultado, la tabla y un arbol si la entrada es valida
    size = len(tokens)
    if size == 0:
        tree = (start, "e") if () in grammar[start] else None
        return tree is not None, [], tree

    terminal_rules, binary_rules = build_indexes(grammar)
    # Cada celda guarda una forma de construir cada variable de ese intervalo
    table = [[{} for _ in range(size)] for _ in range(size)]
    for index, token in enumerate(tokens):
        for head in terminal_rules.get(token, []):
            table[index][index][head] = token

    for length in range(2, size + 1):
        for left in range(size - length + 1):
            right = left + length - 1
            for split in range(left, right):
                for first in table[left][split]:
                    for second in table[split + 1][right]:
                        for head in binary_rules.get((first, second), []):
                            if head not in table[left][right]:
                                table[left][right][head] = (split, first, second)

    accepted = start in table[0][size - 1]
    tree = build_tree(table, start, 0, size - 1) if accepted else None
    return accepted, table, tree


def build_tree(table, head, left, right):
    # Reconstruye un arbol siguiendo las divisiones guardadas en la tabla
    if left == right:
        return head, table[left][right][head]
    split, first, second = table[left][right][head]
    return (
        head,
        build_tree(table, first, left, split),
        build_tree(table, second, split + 1, right),
    )


def format_tree(tree, depth=0):
    # Prepara el arbol como texto con sangria para mostrar sus niveles
    lines = ["  " * depth + tree[0]]
    for child in tree[1:]:
        if isinstance(child, tuple):
            lines.append(format_tree(child, depth + 1))
        else:
            lines.append("  " * (depth + 1) + child)
    return "\n".join(lines)


def format_table(tokens, table):
    # Muestra las variables que reconocen cada fragmento de la entrada
    lines = []
    for length in range(1, len(tokens) + 1):
        lines.append(f"Longitud {length}:")
        for left in range(len(tokens) - length + 1):
            right = left + length - 1
            span = " ".join(tokens[left:right + 1])
            heads = ", ".join(sorted(table[left][right])) or "vacio"
            lines.append(f"  [{left + 1}, {right + 1}] {span} => {{{heads}}}")
    return "\n".join(lines) if lines else "Cadena vacia: no se construye tabla."
