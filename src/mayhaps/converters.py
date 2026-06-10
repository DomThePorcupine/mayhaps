def to_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def to_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def to_str(value: object) -> str:
    return str(value)


def to_percent(value: int | float) -> str:
    return f"{value}%"
