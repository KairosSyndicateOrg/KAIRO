from pydantic import BaseModel, Field
from typing import Literal


class Goal(BaseModel):
    id: str
    description: str
    success_criteria: str
    open_ended: bool = False


class Action(BaseModel):
    action: Literal[
        "hotkey",
        "press",
        "type",
        "click_target",
        "wait",
        "done"
    ]

    goal_id: str | None = None

    keys: list[str] | None = None
    key: str | None = None
    text: str | None = None
    target: str | None = None
    seconds: float | None = None

    expected: str | None = None


class ActionPlan(BaseModel):
    goals: list[Goal] = Field(min_length=1)
    actions: list[Action] = Field(min_length=1)