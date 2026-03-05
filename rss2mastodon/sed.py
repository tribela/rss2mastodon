import re


class SedRule:
    def __init__(self, pattern: re.Pattern, replacement: str, count: int):
        self.pattern = pattern
        self.replacement = replacement
        self.count = count

    def apply(self, text: str) -> str:
        return self.pattern.sub(self.replacement, text, count=self.count)


def parse_sed_expression(expr: str) -> SedRule:
    """Parse a sed-style s/pattern/replacement/flags expression."""
    expr = expr.strip()
    if not expr.startswith('s'):
        raise ValueError(f'Not a sed substitution expression: {expr}')

    delimiter = expr[1]
    parts = []
    current: list[str] = []
    i = 2
    while i < len(expr):
        if expr[i] == '\\' and i + 1 < len(expr):
            current.append(expr[i:i + 2])
            i += 2
        elif expr[i] == delimiter:
            parts.append(''.join(current))
            current = []
            i += 1
        else:
            current.append(expr[i])
            i += 1

    if current:
        parts.append(''.join(current))

    if len(parts) < 2:
        raise ValueError(f'Invalid sed expression: {expr}')

    pattern_str = parts[0]
    replacement = parts[1]
    flags_str = parts[2] if len(parts) > 2 else ''

    re_flags = 0
    count = 1
    for flag in flags_str:
        if flag == 'g':
            count = 0
        elif flag == 'i':
            re_flags |= re.IGNORECASE
        elif flag == 'm':
            re_flags |= re.MULTILINE
        elif flag == 's':
            re_flags |= re.DOTALL
        else:
            raise ValueError(f'Unknown flag: {flag}')

    pattern = re.compile(pattern_str, re_flags)
    return SedRule(pattern, replacement, count)


def parse_sed_expressions(text: str) -> list[SedRule]:
    """Parse multiple sed expressions separated by semicolons."""
    rules = []
    for expr in text.split(';'):
        expr = expr.strip()
        if expr:
            rules.append(parse_sed_expression(expr))
    return rules


def apply_sed_rules(text: str, rules: list[SedRule]) -> str:
    for rule in rules:
        text = rule.apply(text)
    return text
