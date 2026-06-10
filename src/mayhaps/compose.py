from typing import Callable, TypeVar

T = TypeVar("T")

def compose(param: T | None, *dependencies: Callable[[T], T | None]) -> T | None:
    result = param
    if result is None:
        return None
    for dependency in dependencies:
        result = dependency(result)
        if result is None:
            return None
    return result
