class ParseError(Exception):
    """Синтаксическая ошибка при разборе выражения."""
    pass


class EvalError(Exception):
    """Ошибка при вычислении (деление на ноль, некорректные типы и т.п.)."""
    pass


# Парсер: вспомогательный поток токенов
class TokenStream:
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ('EOF', None)

    def eat(self, kind: str, value=None):
        tok = self.peek()
        if tok[0] != kind:
            raise ParseError(f"Ожидался токен типа {kind}, получил {tok}")
        if value is not None and tok[1] != value:
            raise ParseError(f"Ожидался токен {value}, получил {tok}")
        self.pos += 1
        return tok


def tokenize(expression: str) -> list:
    """
    Превращает строку expr в список токенов.
    Токены: ('NUM', int|float) | ('OP','+|-|*|/|//|%|**') | ('LPAREN','(') | ('RPAREN',')') | ('EOF', None)
    Правила чисел: 123 или 123.45 (не поддерживаем .5 и 12.)
    """
    tokens = []
    i = 0
    n = len(expression)

    while i < n:
        ch = expression[i]

        # Пробелы
        if ch.isspace():
            i += 1
            continue

        # Числа: 123 или 123.45
        if ch.isdigit():
            start = i
            # целая часть
            while i < n and expression[i].isdigit():
                i += 1

            # дробная часть (если есть)
            if i < n and expression[i] == '.':
                # должна быть хотя бы одна цифра после точки
                if i + 1 >= n or not expression[i + 1].isdigit():
                    raise ParseError(f"Ожидалась цифра после точки в числе на позиции {i}")
                i += 1  # пропускаем точку
                while i < n and expression[i].isdigit():
                    i += 1
                num_str = expression[start:i]
                try:
                    val = float(num_str)
                except ValueError:
                    raise ParseError(f"Некорректное число '{num_str}'")
                tokens.append(('NUM', val))
            else:
                num_str = expression[start:i]
                try:
                    val = int(num_str)
                except ValueError:
                    raise ParseError(f"Некорректное число '{num_str}'")
                tokens.append(('NUM', val))
            continue

        # Скобки
        if ch == '(':
            tokens.append(('LPAREN', '('))
            i += 1
            continue
        if ch == ')':
            tokens.append(('RPAREN', ')'))
            i += 1
            continue

        # Операторы: **, *, //, /, +, -, %
        if ch == '*':
            if i + 1 < n and expression[i + 1] == '*':
                tokens.append(('OP', '**'))
                i += 2
            else:
                tokens.append(('OP', '*'))
                i += 1
            continue

        if ch == '/':
            if i + 1 < n and expression[i + 1] == '/':
                tokens.append(('OP', '//'))
                i += 2
            else:
                tokens.append(('OP', '/'))
                i += 1
            continue

        if ch in '+-%':
            tokens.append(('OP', ch))
            i += 1
            continue

        # Неизвестный символ
        raise ParseError(f"Недопустимый символ '{ch}' на позиции {i}")

    tokens.append(('EOF', None))
    return tokens


# Правила: unary и primary
def parse_primary(ts: TokenStream):
    tok = ts.peek()
    if tok[0] == 'NUM':
        ts.eat('NUM')
        return tok[1]  # возвращаем число (int или float)
    if tok[0] == 'LPAREN':
        ts.eat('LPAREN', '(')
        val = parse_expr(ts)
        ts.eat('RPAREN', ')')
        return val
    raise ParseError(f"Ожидалось число или '(', получил {tok}")


def parse_unary(ts: TokenStream):
    tok = ts.peek()
    if tok == ('OP', '+'):
        ts.eat('OP', '+')
        return +parse_unary(ts)
    if tok == ('OP', '-'):
        ts.eat('OP', '-')
        return -parse_unary(ts)
    return parse_primary(ts)


# Правила: pow, mul, add, expr
def parse_pow(ts: TokenStream):
    """
    pow → unary (** pow)?
    Право-ассоциативный: 2**3**2 = 2**(3**2) = 512
    """
    left = parse_unary(ts)
    tok = ts.peek()
    if tok == ('OP', '**'):
        ts.eat('OP', '**')
        right = parse_pow(ts)  # рекурсия вправо для правой ассоциативности
        # Возводим в степень
        return left ** right
    return left


def _apply_mul_op(op, a, b):
    # Деление на ноль
    if op in ('/', '//', '%') and b == 0:
        raise EvalError("Деление на ноль")
    if op == '*':
        return a * b
    if op == '/':
        return a / b  # вещественное деление
    if op == '//':
        # По ТЗ: // только для целых
        if not (isinstance(a, int) and isinstance(b, int)):
            raise EvalError("// доступно только для целых")
        return a // b
    if op == '%':
        # По ТЗ: % только для целых
        if not (isinstance(a, int) and isinstance(b, int)):
            raise EvalError("% доступно только для целых")
        return a % b
    raise ParseError(f"Неизвестный оператор умножения/деления: {op}")


def parse_mul(ts: TokenStream):
    """
    mul → pow ((*|/|//|%) pow)*
    Левая ассоциативность.
    """
    value = parse_pow(ts)
    while True:
        tok = ts.peek()
        if tok[0] == 'OP' and tok[1] in ('*', '/', '//', '%'):
            op = tok[1]
            ts.eat('OP', op)
            rhs = parse_pow(ts)
            value = _apply_mul_op(op, value, rhs)
        else:
            break
    return value


def parse_add(ts: TokenStream):
    """
    add → mul ((+|-) mul)*
    Левая ассоциативность.
    """
    value = parse_mul(ts)
    while True:
        tok = ts.peek()
        if tok == ('OP', '+'):
            ts.eat('OP', '+')
            rhs = parse_mul(ts)
            value = value + rhs
        elif tok == ('OP', '-'):
            ts.eat('OP', '-')
            rhs = parse_mul(ts)
            value = value - rhs
        else:
            break
    return value


def parse_expr(ts: TokenStream):
    """
    expr → add
    """
    return parse_add(ts)


def calculate_expression(expression: str):
    tokens = tokenize(expression)
    ts = TokenStream(tokens)
    result = parse_expr(ts)
    # Проверяем, что всё выражение израсходовано
    if ts.peek()[0] != 'EOF':
        raise ParseError(f"Лишние символы после корректного выражения: {ts.peek()}")
    return result
