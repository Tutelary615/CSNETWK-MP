"""
LIFO stack for spells, abilities, and triggered abilities
Note: this class only holds the value of the stack, priority_manager is the one handling it
"""
from dataclasses import dataclass, field

@dataclass
class StackItem:
    stack_item_id: str
    item_type: str
    source_id: str
    controller_id: str
    targets: list[str] = field(default_factory=list)

class Stack:
    def __init__(self):
        self._items: list[StackItem] = []  # index 0 = bottom

    def push(self, item: StackItem) -> None:
        self._items.append(item)

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