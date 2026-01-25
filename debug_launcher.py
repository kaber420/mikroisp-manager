
import sys
import os
import multiprocessing
import traceback

print("1. Setting up paths...")
sys.path.append(os.getcwd())

try:
    print("2. Importing ServiceManager...")
    from launcher.services import ServiceManager
    print("   Success.")
except Exception:
    traceback.print_exc()

try:
    print("3. Importing TUIApp...")
    from launcher.tui.app import TUIApp
    print("   Success.")
except Exception:
    traceback.print_exc()

try:
    print("4. Testing ServiceManager Init...")
    q = multiprocessing.Queue()
    class MockArgs:
        headless = False
    sm = ServiceManager(q, MockArgs())
    print("   Success. Server Info:", sm.server_info)
except Exception:
    traceback.print_exc()

print("Done.")
