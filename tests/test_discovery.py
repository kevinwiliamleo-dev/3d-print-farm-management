"""
Fast Printer Discovery Test Script
Tests the improved discovery service
"""
import sys
import time
sys.path.insert(0, '.')

print('=' * 60)
print('  FAST Printer Discovery Test')
print('=' * 60)
print()

print('[1] Importing discovery service...', end=' ', flush=True)
from src.services.discovery_service import discovery_service
print('OK')

print('[2] Running fast scan (max 5 seconds)...')
start = time.time()
printers = discovery_service.scan_network(timeout=5.0)
elapsed = time.time() - start
print(f'    Completed in {elapsed:.1f} seconds')
print()

print('=' * 60)
print(f'  RESULT: Found {len(printers)} printer(s)')
print('=' * 60)

for p in printers:
    print(f'  - ID: {p.get("printer_id")}')
    print(f'    IP: {p.get("ip_address")}')
    print(f'    Method: {p.get("discovery_method", "unknown")}')
    print()

if not printers:
    print('  No printers found automatically.')
    print()
    print('  TIP: If your printer is on, try manual discovery:')
    print('       POST /api/printers/discover/by-ip')
    print('       with your printer IP address')
    print()
    print('  Or check your printer IP in:')
    print('  - Router admin page')
    print('  - Printer Settings > Network')
    print('  - Bambu Handy app')
