#!/usr/bin/env python3
import requests
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_status(status):
    """Format printer status untuk display"""
    output = []
    output.append("=" * 70)
    output.append(f"🖨️  PRINTER STATUS - LIVE UPDATE")
    output.append("=" * 70)
    output.append("")
    
    # Connection Status
    connected = "🟢 CONNECTED" if status['mqtt_connected'] else "🔴 DISCONNECTED"
    output.append(f"Connection:        {connected}")
    output.append(f"Printer ID:        {status['printer_id']}")
    output.append(f"Status:            {status['printer_status'].upper()}")
    output.append("")
    
    # Progress
    progress = status['print_progress']
    bar_length = 50
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    output.append(f"Progress:          [{bar}] {progress}%")
    output.append("")
    
    # Temperatures
    output.append("TEMPERATURES:")
    output.append(f"  Nozzle:          {status['nozzle_temp']:.1f}°C / {status['nozzle_target_temp']:.1f}°C")
    output.append(f"  Bed:             {status['bed_temp']:.1f}°C / {status['bed_target_temp']:.1f}°C")
    output.append(f"  Chamber:         {status['chamber_temp']:.1f}°C")
    output.append("")
    
    output.append("=" * 70)
    output.append("Press CTRL+C to exit")
    output.append("=" * 70)
    
    return "\n".join(output)

def main():
    printer_id = "03900D5A2402051"
    url = f"http://localhost:5000/api/print-control/{printer_id}/mqtt-status"
    
    print("Starting live status monitor...")
    time.sleep(2)
    
    try:
        while True:
            try:
                clear_screen()
                r = requests.get(url, timeout=5)
                status = r.json()
                print(format_status(status))
                time.sleep(2)  # Update setiap 2 detik
            except requests.exceptions.RequestException as e:
                clear_screen()
                print(f"❌ Error connecting to API: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\n✋ Status monitor stopped.")

if __name__ == "__main__":
    main()
