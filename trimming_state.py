import threading
from typing import Set

class TrimmingState:
    def __init__(self):
        self._lock = threading.Lock()
        self._processing_substances: Set[int] = set()
        self._periodic_update_running = False

    def start_processing(self, substance_id: int) -> None:
        with self._lock:
            self._processing_substances.add(substance_id)

    def stop_processing(self, substance_id: int) -> None:
        with self._lock:
            self._processing_substances.discard(substance_id)

    def is_processing(self, substance_id: int) -> bool:
        with self._lock:
            return substance_id in self._processing_substances

    def stop_all_processing(self) -> None:
        with self._lock:
            self._processing_substances.clear()
            self._periodic_update_running = True

    def finish_periodic_update(self) -> None:
        with self._lock:
            self._periodic_update_running = False

    def is_periodic_update_running(self) -> bool:
        with self._lock:
            return self._periodic_update_running

# Create global instance
trimming_state = TrimmingState()