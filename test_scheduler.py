# test_scheduler.py
# Simple test to verify the scheduler works
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("Testing scheduler import...")
try:
    from app.scheduler import run_scheduler
    print("✅ Scheduler imported successfully")
    
    from app.services.monitor_job import run_monitor_cycle
    print("✅ Monitor job imported successfully")
    
    from app.services.billing_job import run_billing_check
    print("✅ Billing job imported successfully")
    
    print("\n🧪 Testing single monitor cycle...")
    run_monitor_cycle()
    print("✅ Monitor cycle completed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
