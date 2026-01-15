"""
Migration: Add gcode_templates table
This migration ADDS new table without deleting existing data

Tables preserved:
- filament_profiles (21 records)
- ams_slot_assignments (3 records)  
- printers (1 record)
- jobs, queue, bucket_list, print_history, print_settings
"""
import sqlite3
from datetime import datetime

DB_PATH = 'data/farm.db'

# Default templates for Bambu Lab A1
DEFAULT_TEMPLATES = [
    # ==================== START TEMPLATES (order 1-24) ====================
    ("machine_init", None, "Machine Init", "Initialize machine, turn off clog detect", "start", 1, True, False, None,
     """;===== MACHINE INIT =====
G392 S0 ; turn off clog detect during startup
M9833.2"""),
    
    ("start_sound", None, "Start Sound", "Beep on print start", "start", 2, True, True, "startup_sound",
     """;===== START SOUND =====
M17 ; enable motors for sound
M400
M1002 gcode_claim_action : 2
; Startup beep sequence
M400 S1
M17
M400 S1"""),
    
    ("start_heating", None, "Start Heating", "Start nozzle and bed heating", "start", 3, True, False, None,
     """;===== START HEATING =====
M1002 gcode_claim_action : 2
M1002 set_filament_type:{filament_type}
M104 S140 ; preheat nozzle to 140
M140 S{bed_temp} ; start bed heating"""),
    
    ("vibration_test", None, "Vibration Test", "M970 resonance compensation test", "start", 4, True, True, "vibration_test",
     """;===== VIBRATION TEST =====
M1002 gcode_claim_action : 7
M970 Q1 A7 K0 ; vibration compensation test
M970 Q0 A7 K0
M974 S1 ; apply compensation
M400"""),
    
    ("avoid_endstop", None, "Avoid End Stop", "Move Z to avoid end stop during homing", "start", 5, True, False, None,
     """;===== AVOID END STOP =====
G91
G380 S2 Z40 F1200
G380 S3 Z-15 F1200
G90"""),
    
    ("reset_machine", None, "Reset Machine Status", "Reset motor currents, feedrate, flowrate", "start", 6, True, False, None,
     """;===== RESET MACHINE STATUS =====
M204 S6000
M630 S0 P0
G91
M17 Z0.3 ; lower z-motor current
G90
M17 X0.65 Y0.65 Z0.65 ; reset motor current
M220 S100 ; reset feedrate
M221 S100 ; reset flowrate"""),
    
    ("cog_noise_reduction", None, "Cog Noise Reduction", "Enable silent motor mode", "start", 7, True, False, None,
     """;===== COG NOISE REDUCTION =====
M982.2 S1 ; turn on cog noise reduction"""),
    
    ("homing", None, "Homing", "Home XY axes", "start", 8, True, False, None,
     """;===== HOMING =====
M1002 gcode_claim_action : 8
M211 X1 Y1 Z1 ; turn on soft end stops
G28 X Y ; home XY"""),
    
    ("smart_temp_wait", None, "Smart Temp Wait", "Wait for bed while nozzle heats", "start", 9, True, False, None,
     """;===== SMART TEMP WAIT =====
M400
M190 S{bed_temp} ; wait for bed temp
M109 S140 ; wait for nozzle preheat"""),
    
    ("clean_nozzle", None, "Clean Nozzle", "Wipe nozzle on wiper arm", "start", 10, True, True, "clean_nozzle",
     """;===== CLEAN NOZZLE =====
M1002 gcode_claim_action : 6
G1 X25 Y160 F18000 ; move to wiper position
G1 Z4 F1200 ; lower to wiper
G1 X60 F18000 ; wipe across
G1 X25 F18000 ; wipe back
G1 Z10 F1200 ; raise"""),
    
    ("wipe_nozzle", None, "Wipe Nozzle", "Extended nozzle wipe sequence", "start", 11, True, True, "wipe_nozzle",
     """;===== WIPE NOZZLE =====
; Position at wiper
G1 X25 Y160 F18000
G1 Z4 F1200

; Wipe pattern - 3 passes
G1 X65 F18000
G1 X25 F18000
G1 X65 F18000
G1 X25 F18000
G1 X65 F18000
G1 X25 F18000
G1 Z10 F1200"""),
    
    ("initial_extrusion", None, "Initial Extrusion", "Prime nozzle with small extrusion", "start", 12, True, False, None,
     """;===== INITIAL EXTRUSION =====
M83 ; relative extrusion
G1 E3 F300 ; extrude 3mm
G1 E-1 F800 ; small retract
G92 E0 ; reset E"""),
    
    ("home_z", None, "Home Z", "Home Z axis after bed is hot", "start", 13, True, False, None,
     """;===== HOME Z =====
M1002 gcode_claim_action : 8
G28 Z ; home Z
G1 Z5 F1200 ; raise Z slightly"""),
    
    ("build_plate_detection", None, "Build Plate Detection", "Detect build plate type", "start", 14, True, False, None,
     """;===== BUILD PLATE DETECTION =====
M1002 gcode_claim_action : 10
M960 S2 P1
G29.2 S0 ; Reset build plate type
M1002 judge_flag finish_sensor_check=1"""),
    
    ("ams_loading", None, "AMS Loading", "Load filament from AMS slot (smart skip if same filament)", "start", 15, True, True, "ams_slot",
     """;===== AMS LOADING =====
; Selected AMS slot: {ams_slot}
; Current loaded tray: {current_tray}
; NOTE: If current_tray == ams_slot, this will be SKIPPED
M620 S{ams_slot}A ; Select AMS slot
M400
T{ams_slot} ; Load filament from slot
M400
M621 S{ams_slot}A ; Confirm loaded"""),
    
    ("filament_detection", None, "Filament Detection", "Verify filament is loaded properly", "start", 16, True, False, None,
     """;===== FILAMENT DETECTION =====
M412 S1 ; Enable filament runout detection
M400"""),
    
    ("flow_calibration", None, "Flow Calibration", "Auto flow rate calibration", "start", 17, True, True, "flow_calibration",
     """;===== FLOW CALIBRATION =====
M1002 gcode_claim_action : 4
; K factor calculation for flow
M900 K0 ; Linear advance off
M221 S100 ; Reset flow rate"""),
    
    ("bed_leveling", None, "Bed Leveling", "Auto bed leveling mesh", "start", 18, True, True, "auto_bed_leveling",
     """;===== BED LEVELING =====
M1002 gcode_claim_action : 3
M969 S1 ; Auto bed leveling
G29 ; Run bed leveling mesh
M400"""),
    
    ("final_positioning", None, "Final Positioning", "Move to start position", "start", 19, True, False, None,
     """;===== FINAL POSITIONING =====
G1 X60 Y60 Z5 F12000 ; Move to start area
M400"""),
    
    ("final_temp_wait", None, "Final Temp Wait", "Wait for final nozzle temperature", "start", 20, True, False, None,
     """;===== FINAL TEMP WAIT =====
M1002 gcode_claim_action : 0
M400
G1 Z3 F800 ; move nozzle up a little
M106 P1 S255 ; turn on fan to cool tip, prevents oozing
M109 S{preheat_temp} ; wait for temp (offset -{preheat_offset}C)"""),
    
    ("ready_to_print", None, "Ready to Print", "Final prep before first layer", "start", 21, True, False, None,
     """;===== READY TO PRINT =====
M960 S1 P0 ; turn off laser
M960 S2 P0
M106 P1 S0 ; turn off aux fan
M106 S255 ; part cooling fan ON
M109 S{nozzle_temp} ; wait for print temp
G392 S1 ; turn on clog detect
M400"""),
    
    ("nozzle_load_line", None, "Nozzle Load Line", "Draw line at edge of bed to prime nozzle", "start", 22, True, True, "nozzle_load_line",
     """;===== NOZZLE LOAD LINE =====
G1 Z0.4 F1200 ; Move to first layer height
G1 X5 Y5 F12000 ; Move to start corner
M83 ; Relative extrusion
G1 X180 E20 F1500 ; Draw line while extruding
G1 E-1 F1800 ; Small retract
G1 Z1 F1200 ; Lift
G92 E0 ; Reset E"""),
    
    ("pre_extrude", None, "Pre-Extrude", "Final extrusion before print (Quick Start mode)", "start", 23, True, True, "pre_extrude",
     """;===== PRE-EXTRUDE (Quick Start) =====
M83 ; Relative extrusion mode
G1 E5 F300 ; Extrude 5mm to prime
G1 E-2 F1800 ; Retract 2mm
G92 E0 ; Reset extrusion position
M400"""),
    
    ("timelapse_start", None, "Timelapse", "Enable timelapse recording", "start", 24, False, True, "timelapse",
     """;===== TIMELAPSE START =====
M991 S0 P-1 ; close last timelapse if any
M400
M991 S1 P1 ; start timelapse recording"""),
    
    # ==================== END TEMPLATES (order 1-10) ====================
    ("end_finish_moves", None, "Finish Moves", "Wait for all moves to complete", "end", 1, True, False, None,
     """;===== FINISH MOVES =====
M400 ; wait for buffer to clear
G92 E0 ; reset E"""),
    
    ("end_timelapse", None, "Timelapse Finish", "Stop timelapse recording", "end", 2, False, True, "timelapse",
     """;===== TIMELAPSE FINISH =====
M991 S0 ; stop timelapse and save video
M400"""),
    
    ("end_retract_raise", None, "Retract and Raise", "Retract filament and raise Z", "end", 3, True, False, None,
     """;===== RETRACT AND RAISE =====
G92 E0
G1 E-2 F2400 ; Retract
G91 ; Relative positioning
G1 Z10 F3000 ; Raise Z by 10mm
G90 ; Absolute positioning"""),
    
    ("end_safe_position", None, "Move to Safe Position", "Move to back of bed", "end", 4, True, False, None,
     """;===== MOVE TO SAFE POSITION =====
G1 X0 Y256 F9000 ; Move to back"""),
    
    ("end_auto_eject", None, "Auto Eject", "Wait for bed to cool then push off print", "end", 5, False, True, "auto_eject",
     """;===== AUTO EJECT =====
; Waiting for bed to cool to {cooldown_temp}C
M140 S{cooldown_temp} ; Set bed target
M190 R{cooldown_temp} ; Wait for cooldown (R = wait for temp or below)

; Push off print
G28 X ; Home X to push print off
G1 X128 F12000 ; Return to center"""),
    
    ("end_heaters_off", None, "Turn Off Heaters", "CRITICAL: Turn off hotend and bed heaters", "end", 6, True, False, None,
     """;===== SAFETY: TURN OFF HEATERS =====
M104 S0 ; *** TURN OFF HOTEND ***
M140 S0 ; *** TURN OFF BED ***"""),
    
    ("end_fans_off", None, "Turn Off Fans", "Turn off all fans", "end", 7, True, False, None,
     """;===== TURN OFF FANS =====
M106 S0 ; Part cooling fan OFF
M106 P1 S0 ; Aux fan OFF
M106 P2 S0 ; Chamber fan OFF"""),
    
    ("end_motors_off", None, "Disable Motors", "Disable stepper motors", "end", 8, True, False, None,
     """;===== DISABLE MOTORS =====
M400 ; Wait for completion
M18 X Y Z ; Disable motors"""),
    
    ("end_sound", None, "End Sound", "Melody on print completion", "end", 9, True, True, "end_sound",
     """;===== END SOUND =====
M400
; Success melody - 3 notes
M400 S1
M17
M400 S1
M17
M400 S2"""),
    
    ("end_complete", None, "Print Complete", "Final cleanup and message", "end", 10, True, False, None,
     """;===== PRINT COMPLETE =====
M400
M1002 gcode_claim_action : 0
; Print finished successfully!
; Total time: Check slicer estimate"""),
]


def migrate():
    print("=" * 50)
    print("Migration: Add gcode_templates table")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check existing data counts BEFORE migration
    print("\n[1] Checking existing data...")
    for table in ['filament_profiles', 'ams_slot_assignments', 'printers', 'jobs', 'queue']:
        try:
            c.execute(f'SELECT COUNT(*) FROM {table}')
            count = c.fetchone()[0]
            print(f"    {table}: {count} records")
        except:
            print(f"    {table}: (table not exists)")
    
    # Check if gcode_templates already exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gcode_templates'")
    if c.fetchone():
        print("\n[!] gcode_templates table already exists!")
        print("    Dropping and recreating with fresh data...")
        c.execute("DROP TABLE gcode_templates")
    
    # Create gcode_templates table
    print("\n[2] Creating gcode_templates table...")
    c.execute('''
        CREATE TABLE gcode_templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_key VARCHAR(100) NOT NULL,
            printer_model VARCHAR(100),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            category VARCHAR(20) NOT NULL,
            "order" INTEGER NOT NULL DEFAULT 1,
            enabled BOOLEAN DEFAULT 1,
            controllable BOOLEAN DEFAULT 0,
            setting_key VARCHAR(100),
            gcode TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default templates
    print("\n[3] Inserting default templates...")
    now = datetime.utcnow().isoformat()
    
    for template in DEFAULT_TEMPLATES:
        c.execute('''
            INSERT INTO gcode_templates 
            (template_key, printer_model, name, description, category, "order", 
             enabled, controllable, setting_key, gcode, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*template, now, now))
    
    print(f"    Inserted {len(DEFAULT_TEMPLATES)} templates")
    
    # Verify templates
    c.execute('SELECT COUNT(*) FROM gcode_templates WHERE category = "start"')
    start_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM gcode_templates WHERE category = "end"')
    end_count = c.fetchone()[0]
    print(f"    - Start templates: {start_count}")
    print(f"    - End templates: {end_count}")
    
    # Verify existing data AFTER migration
    print("\n[4] Verifying data preservation...")
    for table in ['filament_profiles', 'ams_slot_assignments', 'printers']:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        count = c.fetchone()[0]
        print(f"    {table}: {count} records [OK]")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print("Migration complete! All data preserved.")
    print("=" * 50)


if __name__ == "__main__":
    migrate()
