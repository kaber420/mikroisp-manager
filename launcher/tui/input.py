import sys
import termios
import tty
import select

class InputHelper:
    def __init__(self):
        self.old_settings = None

    def __enter__(self):
        try:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except termios.error:
            # Fallback for non-interactive shells (e.g. docker log viewing)
            self.old_settings = None
        return self

    def __exit__(self, type, value, traceback):
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        if not self.old_settings:
            return None
        
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None
