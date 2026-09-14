from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InvocationMode = Literal["unsupported-rest", "manual-actor", "future-test-boundary"]


@dataclass(frozen=True, slots=True)
class CommandContract:
    name: str
    area: str
    invocation: InvocationMode
    destructive: bool = False
    notes: str = ""


COMMANDS: tuple[CommandContract, ...] = (
    CommandContract("setup", "environment", "manual-actor", notes="Interactive select/button workflow."),
    CommandContract("build", "server", "manual-actor", notes="Mutates many roles/channels; observe with snapshots."),
    CommandContract("addstream", "streams", "manual-actor", notes="Target one stream."),
    CommandContract("removestream", "streams", "manual-actor", destructive=True, notes="Scoped destructive operation."),
    CommandContract("resetserver", "reset", "manual-actor", destructive=True, notes="Owner-only destructive operation."),
    CommandContract("assignstudent", "students", "manual-actor"),
    CommandContract("studenthistory", "students", "manual-actor"),
    CommandContract("leave_school", "students", "manual-actor"),
    CommandContract("assignteacher", "teachers", "manual-actor"),
    CommandContract("assignteacherfull", "teachers", "manual-actor"),
    CommandContract("assignsubjectteachers", "teachers", "manual-actor"),
    CommandContract("set_timetable", "academic", "manual-actor", notes="Requires a real Discord attachment input."),
    CommandContract("setexam", "academic", "manual-actor"),
    CommandContract("reportabsence", "academic", "manual-actor"),
    CommandContract("status", "observation", "manual-actor", notes="Can be independently verified by snapshots/state."),
    CommandContract("years", "academic", "manual-actor"),
    CommandContract("newyear", "academic", "manual-actor", destructive=True, notes="Changes active academic-year state."),
    CommandContract("rollbackyear", "academic", "manual-actor", destructive=True, notes="Changes academic-year state."),
)


def get_command(name: str) -> CommandContract:
    normalized = name.strip().lstrip("/").casefold()
    for command in COMMANDS:
        if command.name.casefold() == normalized:
            return command
    raise KeyError(f"Unknown School Manager command: {name}")
