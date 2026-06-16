from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from mayhaps.result import Ok, ValidationErr

__all__ = ["parse", "ValidationErr"]


def parse[M: BaseModel](model_class: type[M]) -> Callable[[dict[str, Any]], Ok[M] | ValidationErr]:
    """Step factory: validate a dict into a Pydantic BaseModel.

    On success returns Ok(instance). On validation failure returns ValidationErr
    with a human-readable detail string and a list of the failing field paths.
    """
    def step(data: dict[str, Any]) -> Ok[M] | ValidationErr:
        try:
            return Ok(model_class.model_validate(data))
        except ValidationError as exc:
            errors = exc.errors()
            fields = [".".join(str(loc) for loc in e["loc"]) for e in errors if e["loc"]]
            detail = "; ".join(
                (".".join(str(loc) for loc in e["loc"]) + ": " if e["loc"] else "") + e["msg"]
                for e in errors
            )
            return ValidationErr(detail, fields=fields)
    return step
