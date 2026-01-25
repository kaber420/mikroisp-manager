import sys
import termios
import tty
import os
import select
import datetime

class InputHelper:
    def __init__(self):
        self.old_settings = None
        self.fd = sys.stdin.fileno()
        self.buffer = ""

    def __enter__(self):
        try:
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        except Exception as e:
            self.old_settings = None
        return self

    def __exit__(self, type, value, traceback):
        if self.old_settings:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(self):
        if not self.old_settings:
            return None
        
        # Check if data avail using select (Non-blocking check)
        # Timeout 0 = return immediately
        r, w, x = select.select([self.fd], [], [], 0)
        
        if self.fd in r:
            try:
                chunk = os.read(self.fd, 1024)
                if chunk:
                    self.buffer += chunk.decode('utf-8', errors='ignore')
            except OSError:
                pass
            
        if not self.buffer:
            return None
            
        # --- Parsing Logic (Kept from previous fix) ---
        
        if self.buffer.startswith('\x1b'):
            # Check for CSI/SS3
            if len(self.buffer) >= 3:
                seq = self.buffer[:3]
                key = None
                if seq in ['\x1b[A', '\x1bOA']: key = 'KEY_UP'
                elif seq in ['\x1b[B', '\x1bOB']: key = 'KEY_DOWN'
                elif seq in ['\x1b[C', '\x1bOC']: key = 'KEY_RIGHT'
                elif seq in ['\x1b[D', '\x1bOD']: key = 'KEY_LEFT'
                
                if key:
                    self.buffer = self.buffer[3:]
                    return key
            
            # Isolated ESC check
            if len(self.buffer) > 1:
                if self.buffer[1] not in ['[', 'O']:
                    self.buffer = self.buffer[1:]
                    return 'KEY_ESC'
            else:
                # Buffer is just ESC.
                # If we are here, we read all available input from OS.
                # So it's likely just an ESC key.
                self.buffer = self.buffer[1:]
                return 'KEY_ESC'

        # Standard char
        char = self.buffer[0]
        
        if char == '\r' or char == '\n':
            key = '\n'
        else:
            key = char
            
        self.buffer = self.buffer[1:]
        return key

    def _log_debug(self, msg):
        pass
