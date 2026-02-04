"""
Quick system status check
"""
import subprocess
import sqlite3

print("\n" + "="*70)
print("🚀 3D PRINT FARM - SYSTEM STATUS")
print("="*70)

# Check servers
print("\n📡 SERVERS:")
backend_running = False
frontend_running = False

try:
    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
    if ':5051' in result.stdout and 'LISTENING' in result.stdout:
        print("  ✅ Backend  (port 5051) - RUNNING")
        backend_running = True
    else:
        print("  ❌ Backend  (port 5051) - NOT RUNNING")
except:
    print("  ⚠️  Backend  - Cannot check")

try:
    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
    if ':3051' in result.stdout and 'LISTENING' in result.stdout:
        print("  ✅ Frontend (port 3051) - RUNNING")
        frontend_running = True
    else:
        print("  ❌ Frontend (port 3000) - NOT RUNNING")
except:
    print("  ⚠️  Frontend - Cannot check")

# Check database
print("\n💾 DATABASE:")
try:
    conn = sqlite3.connect('data/farm.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM printers")
    printer_count = cursor.fetchone()[0]
    print(f"  📟 Printers: {printer_count}")
    
    cursor.execute("SELECT COUNT(*) FROM jobs")
    job_count = cursor.fetchone()[0]
    print(f"  📋 Jobs: {job_count}")
    
    cursor.execute("SELECT COUNT(*) FROM queue")
    queue_count = cursor.fetchone()[0]
    print(f"  📝 Queue: {queue_count}")
    
    cursor.execute("SELECT COUNT(*) FROM print_history")
    history_count = cursor.fetchone()[0]
    print(f"  📊 History: {history_count}")
    
    conn.close()
except Exception as e:
    print(f"  ❌ Database error: {e}")

# Check printer status
print("\n🖨️  PRINTER STATUS:")
try:
    conn = sqlite3.connect('data/farm.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT printer_id, status, print_progress, print_stage FROM printers")
    printers = cursor.fetchall()
    
    if printers:
        for printer_id, status, progress, stage in printers:
            emoji = "🟢" if status == "idle" else "🔴" if status == "offline" else "🟡"
            print(f"  {emoji} {printer_id}")
            print(f"     Status: {status}")
            print(f"     Progress: {progress}%")
            print(f"     Stage: {stage}")
    else:
        print("  ⚠️  No printers configured")
    
    conn.close()
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check queue status
print("\n📝 QUEUE STATUS:")
try:
    conn = sqlite3.connect('data/farm.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, COUNT(*) FROM queue GROUP BY status")
    statuses = cursor.fetchall()
    
    if statuses:
        for status, count in statuses:
            emoji = "✅" if status == "completed" else "🔄" if status == "running" else "⏳"
            print(f"  {emoji} {status}: {count}")
    else:
        print("  📭 Queue is empty")
    
    # Check for stuck items
    cursor.execute("SELECT queue_id, current_loop FROM queue WHERE status='running'")
    stuck = cursor.fetchall()
    if stuck:
        print(f"\n  ⚠️  WARNING: {len(stuck)} items stuck in 'running' status")
        for qid, loop in stuck:
            print(f"     Queue {qid}: loop {loop}")
    
    conn.close()
except Exception as e:
    print(f"  ❌ Error: {e}")

# System health
print("\n" + "="*70)
if backend_running and frontend_running:
    print("✅ SYSTEM HEALTHY - All services running")
    print("\n🌐 Access the system:")
    print("   Backend:  http://localhost:5051")
    print("   Frontend: http://localhost:3051")
else:
    print("⚠️  SYSTEM ISSUE - Some services not running")
    if not backend_running:
        print("   ❌ Backend needs to be started")
    if not frontend_running:
        print("   ❌ Frontend needs to be started")
    print("\n   Run: start-all.bat")

print("="*70 + "\n")
