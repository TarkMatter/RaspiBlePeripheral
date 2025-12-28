class SimpleQueue:
    def __init__(self):
        self._items = []

    def put_nowait(self, item):
        self._items.append(item)

    def get_nowait(self):
        if not self._items:
            return None
        return self._items.pop(0)

    def empty(self):
        return len(self._items) == 0