import threading
import uuid
import logging

logger = logging.getLogger(__name__)


class TrainingQueue:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._active = 0
        self._waiting = []
        self._acquired = set()

    def enqueue(self):
        ticket = str(uuid.uuid4())
        with self._lock:
            self._waiting.append(ticket)
            pos = self._waiting.index(ticket)
        logger.info(
            "Queued training ticket %s (position=%d, active=%d/%d, waiting=%d)",
            ticket, pos, self._active, self.max_concurrent, len(self._waiting)
        )
        return ticket

    def position(self, ticket):
        """Return 0-indexed queue position, or -1 if not waiting."""
        with self._lock:
            if ticket in self._waiting:
                return self._waiting.index(ticket)
            return -1

    def snapshot(self, ticket):
        """Return (position, active, max_concurrent, waiting_count)."""
        with self._lock:
            position = self._waiting.index(ticket) if ticket in self._waiting else -1
            return position, self._active, self.max_concurrent, len(self._waiting)

    def wait_for_slot(self, ticket, timeout=1.0):
        """Block up to ``timeout`` seconds waiting for this ticket's slot.

        Returns True if the slot was acquired, False if still waiting.
        """
        with self._cond:
            if ticket in self._acquired:
                return True

            def _ready():
                return (
                    self._active < self.max_concurrent
                    and self._waiting
                    and self._waiting[0] == ticket
                )

            if not _ready():
                self._cond.wait(timeout=timeout)

            if _ready():
                self._waiting.pop(0)
                self._active += 1
                self._acquired.add(ticket)
                logger.info(
                    "Acquired training slot for %s (active=%d/%d, waiting=%d)",
                    ticket, self._active, self.max_concurrent, len(self._waiting)
                )
                return True
            return False

    def release(self, ticket):
        with self._cond:
            if ticket in self._acquired:
                self._acquired.discard(ticket)
                self._active = max(0, self._active - 1)
                logger.info(
                    "Released training slot for %s (active=%d/%d, waiting=%d)",
                    ticket, self._active, self.max_concurrent, len(self._waiting)
                )
                self._cond.notify_all()

    def abandon(self, ticket):
        """Remove a ticket that never acquired a slot (client disconnect)."""
        with self._cond:
            if ticket in self._waiting:
                self._waiting.remove(ticket)
                logger.info("Abandoned queued ticket %s", ticket)
                self._cond.notify_all()
            elif ticket in self._acquired:
                self.release(ticket)


training_queue = TrainingQueue(max_concurrent=3)
