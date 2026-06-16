from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from mayhaps.result import Err, Ok

__all__ = ["parse"]


def parse[M: BaseModel](model_class: type[M]) -> Callable[[dict[str, Any]], Ok[M] | Err]:
    """Step factory: validate a dict into a Pydantic BaseModel.

    On success returns Ok(instance). On validation failure returns Err with
    a human-readable detail string joining all validation error messages.
    """
    def step(data: dict[str, Any]) -> Ok[M] | Err:
        try:
            return Ok(model_class.model_validate(data))
        except ValidationError as exc:
            messages = "; ".join(
                ".".join(str(loc) for loc in e["loc"]) + ": " + e["msg"]
                if e["loc"]
                else e["msg"]
                for e in exc.errors()
            )
            return Err(messages)
    return step
