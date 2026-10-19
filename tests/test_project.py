import unittest
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory

from cyk import parse
from grammar import is_cnf, load_grammar, to_cnf
from main import read_tokens


ROOT = Path(__file__).resolve().parents[1]


def bounded_language(grammar, start, limit):
    # Calcula palabras cortas directamente desde la CFG para contrastar la CNF
    words = {head: set() for head in grammar}
    changed = True
    while changed:
        changed = False
        for head, bodies in grammar.items():
            for body in bodies:
                options = {()}
                for symbol in body:
                    suffixes = words[symbol] if symbol in grammar else {(symbol,)}
                    options = {
                        left + right for left in options for right in suffixes
                        if len(left) + len(right) <= limit
                    }
                added = options - words[head]
                if added:
                    words[head].update(added)
                    changed = True
    return words[start]


def tree_leaves(tree):
    # Extrae los terminales del arbol en el orden de la entrada
    if len(tree) == 2:
        return [tree[1]]
    return tree_leaves(tree[1]) + tree_leaves(tree[2])


class ProjectTests(unittest.TestCase):
    def check_conversion(self, grammar, start, alphabet, limit=4):
        # Compara la CFG, su CNF y los resultados de CYK para entradas cortas
        expected = bounded_language(grammar, start, limit)
        converted, new_start, _ = to_cnf(grammar, start)
        self.assertTrue(is_cnf(converted, new_start))
        self.assertEqual(expected, bounded_language(converted, new_start, limit))
        for length in range(limit + 1):
            for tokens in product(alphabet, repeat=length):
                accepted, _, _ = parse(tokens, converted, new_start)
                self.assertEqual(accepted, tokens in expected, tokens)

    def test_english_examples(self):
        # Comprueba frases validas y los terminales de sus arboles
        grammar, start = load_grammar(ROOT / "grammars/english.txt")
        grammar, start, _ = to_cnf(grammar, start)
        self.assertTrue(is_cnf(grammar, start))
        for sentence in [
            "she eats a cake with a fork", "the cat drinks the beer",
            "he cooks", "she eats the soup in the oven", "the knife drinks a cat",
        ]:
            with self.subTest(sentence=sentence):
                accepted, _, tree = parse(sentence.split(), grammar, start)
                self.assertTrue(accepted)
                self.assertEqual(tree_leaves(tree), sentence.split())

    def test_english_rejections(self):
        # Comprueba que las frases invalidas se rechacen sin generar un arbol
        grammar, start = load_grammar(ROOT / "grammars/english.txt")
        grammar, start, _ = to_cnf(grammar, start)
        for sentence in ["", "she cake eats", "the cat drinks beer", "she eats a pizza", "she"]:
            with self.subTest(sentence=sentence):
                accepted, _, tree = parse(sentence.split(), grammar, start)
                self.assertFalse(accepted)
                self.assertIsNone(tree)

    def test_supplied_arithmetic_grammars(self):
        # Contrasta las dos gramaticas aritmeticas con ejemplos validos e invalidos
        languages = []
        for filename in ["1.txt", "1-cnf.txt"]:
            grammar, start = load_grammar(ROOT / "grammars" / filename)
            converted, new_start, _ = to_cnf(grammar, start)
            self.assertTrue(is_cnf(converted, new_start))
            languages.append(bounded_language(converted, new_start, 5))
            self.assertEqual(languages[-1], bounded_language(grammar, start, 5))
            for sentence in ["id", "( id * id ) + id", "id + id * id"]:
                self.assertTrue(parse(sentence.split(), converted, new_start)[0])
            for sentence in ["id +", "( id", "id id", "id * + id"]:
                self.assertFalse(parse(sentence.split(), converted, new_start)[0])
        self.assertEqual(*languages)

    def test_repeated_nullable_symbols(self):
        # Revisa que cada aparicion de una variable anulable pueda omitirse
        self.check_conversion({"S": {("A", "A", "B")}, "A": {(), ("a",)}, "B": {("b",)}}, "S", ["a", "b"])

    def test_nullable_start_on_right(self):
        # Revisa un inicio que es recursivo y tambien genera epsilon
        self.check_conversion({"S": {(), ("S", "S"), ("a",)}}, "S", ["a", "b"])

    def test_unit_cycle(self):
        # Comprueba que los ciclos de reglas unitarias se eliminen correctamente
        self.check_conversion({"S": {("A",)}, "A": {("B",)}, "B": {("A",), ("b",)}}, "S", ["b"])

    def test_useless_symbols(self):
        # Verifica la eliminacion de variables improductivas e inalcanzables
        grammar = {"S": {("a",), ("B",)}, "B": {("B", "B")}, "U": {("b",)}}
        self.check_conversion(grammar, "S", ["a", "b", "B"])
        converted, _, _ = to_cnf(grammar, "S")
        self.assertEqual(set(converted), {"S"})

    def test_empty_language(self):
        # Comprueba una gramatica que no genera ninguna palabra
        self.check_conversion({"S": {("A",)}, "A": {("A",)}}, "S", ["a"])

    def test_only_empty_word(self):
        # Comprueba una gramatica que solo genera la cadena vacia
        self.check_conversion({"S": {()}}, "S", ["a"])

    def test_mixed_long_rule(self):
        # Revisa la conversion de reglas largas con terminales y variables
        self.check_conversion({"S": {("a", "A", "b", "A")}, "A": {("a",)}}, "S", ["a", "b"])

    def test_generated_name_collisions(self):
        # Comprueba que los nombres auxiliares no coincidan con simbolos existentes
        grammar = {"S": {("a", "TERM0", "PAIR0", "A")}, "A": {("a",)}}
        self.check_conversion(grammar, "S", ["a", "TERM0", "PAIR0"])

    def test_loader_repeated_heads_and_comments(self):
        # Verifica la lectura de comentarios y reglas con la misma variable
        with TemporaryDirectory() as directory:
            path = Path(directory) / "grammar.txt"
            path.write_text("# example\nS -> A\nA -> a\nA -> e\n", encoding="utf-8-sig")
            grammar, start = load_grammar(path)
            self.assertEqual(start, "S")
            self.assertEqual(grammar["A"], {("a",), ()})

    def test_loader_rejects_invalid_lines(self):
        # Comprueba que los errores de formato se detecten al leer el archivo
        with TemporaryDirectory() as directory:
            path = Path(directory) / "grammar.txt"
            for text in ["", "S A", "S -> a |", "S -> e A", "S A -> a"]:
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaises(ValueError):
                    load_grammar(path)

    def test_sentence_like_statement(self):
        # Verifica las frases del enunciado con mayusculas y punto final
        grammar, start = load_grammar(ROOT / "grammars/english.txt")
        grammar, start, _ = to_cnf(grammar, start)
        for sentence in ["She eats a cake with a fork", "The cat drinks the beer."]:
            self.assertTrue(parse(read_tokens(sentence, grammar), grammar, start)[0])

    def test_ambiguous_grammar(self):
        # Comprueba que una entrada ambigua produzca un arbol valido.
        grammar = {"S": {("A", "B"), ("C", "D")}, "A": {("a",)}, "B": {("b",)}, "C": {("a",)}, "D": {("b",)}}
        accepted, _, tree = parse(["a", "b"], grammar, "S")
        self.assertTrue(accepted)
        self.assertEqual(tree_leaves(tree), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
