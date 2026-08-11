"""
LIFO stack for spells, abilities, and triggered abilities
Note: this class only holds the value of the stack, priority_manager is the one handling it
"""
import itertools
from dataclasses import dataclass, field
from typing import Optional

_id_counter = itertools.count(1)

def _new_stack_id() -> str:
    return f"stk_{next(_id_counter):02d}"

@dataclass
class StackItem:
    stack_item_id: str
    item_type: str
    source_id: str
    controller_id: str
    targets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stack_item_id": self.stack_item_id,
            "item_type": self.item_type,
            "source": self.source_id,
            "controller": self.controller_id,
            "targets": self.targets
        }

class Stack:
    def __init__(self):
        self._items: list[StackItem] = []  # index 0 = bottom

    def push(self, item_type: str, source_id: str,
             controller_id: str, targets: list[str]) -> StackItem:
        item = StackItem(
            stack_item_id = _new_stack_id(),
            item_type = item_type,
            source_id = source_id,
            controller_id = controller_id,
            targets = targets
        )
        self._items.append(item)
        return item

    def pop(self) -> Optional[StackItem]:
        return self._items.pop() if self._items else None

    def peek(self) -> Optional[StackItem]:
        return self._items[-1] if self._items else None

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def clear(self) -> None:
        self._items.clear()

    def to_list(self) -> list[dict]:
        return [item.to_dict() for item in self._items]

    def __len__(self) -> int:
        return len(self._items)