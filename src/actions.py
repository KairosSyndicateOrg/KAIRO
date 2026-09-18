from pydantic import BaseModel, Field
from typing import Literal


class Action(BaseModel):
    action: Literal[
        "hotkey",
        "press",
        "type",
        "click_target",
        "wait",
        "done"
    ]

    keys: list[str] | None = None
    key: str | None = None
    text: str | None = None
    target: str | None = None
    seconds: float | None = None

    expected: str | None = None


class ActionPlan(BaseModel):
    actions: list[Action] = Field(min_length=1)