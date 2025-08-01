import sys
import threading
import time


class Spinner:
    """A simple spinner for CLI loading indicators."""

    def __init__(self, message="Loading... ", delay=0.1):
        self.message = message
        self.delay = delay
        self.spinner_chars = ["|", "/", "-", "\\"]
        self.running = False
        self._thread = None

    def _spin(self):
        idx = 0
        sys.stdout.write(self.message)
        sys.stdout.flush()
        while self.running:
            sys.stdout.write(self.spinner_chars[idx % len(self.spinner_chars)])
            sys.stdout.flush()
            time.sleep(self.delay)
            sys.stdout.write("\b")
            idx += 1
        # Clear spinner character and move to line start
        sys.stdout.write(" ")
        sys.stdout.write("\r")
        sys.stdout.flush()

    def start(self):
        """Begin the spinner in a background thread."""
        self.running = True
        self._thread = threading.Thread(target=self._spin)
        self._thread.start()

    def stop(self):
        """Stop the spinner and wait for the thread to finish."""
        self.running = False
        if self._thread is not None:
            self._thread.join()
