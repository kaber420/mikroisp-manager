
import sys
import os
import time
import multiprocessing
import queue

# Validar entorno
if not os.path.isdir("app"):
    print("Error: Run this from the root directory")
    sys.exit(1)

sys.path.append(os.getcwd())

from launcher.services import ServiceManager

def logger_thread(q):
    while True:
        try:
            record = q.get(timeout=1)
            print(f"[{record.levelname}] {record.msg}")
        except queue.Empty:
            pass
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    print("Starting Services Debugger...")
    log_queue = multiprocessing.Queue()
    
    # Start logger
    p_log = multiprocessing.Process(target=logger_thread, args=(log_queue,))
    p_log.start()
    
    class MockArgs:
        pass
        
    try:
        sm = ServiceManager(log_queue, MockArgs())
        print("ServiceManager initialized.")
        sm.start_all()
        print("All services started. Waiting 15 seconds to capture logs...")
        time.sleep(15)
        print("Stopping services...")
        sm.stop_all()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        if 'sm' in locals():
            sm.stop_all()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        p_log.terminate()
