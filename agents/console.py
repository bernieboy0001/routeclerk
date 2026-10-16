import sys

_COLOR = sys.stdout.isatty()


def _p(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _COLOR else text


def header(text: str) -> str:
    return _p("1;36", text)


def section(title: str, width: int = 68) -> str:
    bar = f"-- {title} "
    return _p("1;36", bar + "-" * max(0, width - len(bar)))


def dim(text: str) -> str:
    return _p("2", text)


def green(text: str) -> str:
    return _p("32", text)


def yellow(text: str) -> str:
    return _p("33", text)


def red(text: str) -> str:
    return _p("31", text)


def bold(text: str) -> str:
    return _p("1", text)


def kv(key: str, value: str, width: int = 22) -> str:
    return f"  {key.ljust(width)} {value}"
