"""
Migration script to update gcode templates with new A1 GCode
Based on FactorianDesigns A1 template - January 2026
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/farm.db")

# New templates based on the provided GCode
NEW_TEMPLATES = [
    # ===== START SEQUENCE =====
    {
        "template_key": "start_machine",
        "name": "Start Machine A1",
        "description": "Initialize A1 machine with G392/M9833 commands",
        "category": "start",
        "order": 1,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start machine: A1 =========================
;===== date: 20250822 ==================
G392 S0
M9833.2
;===== end machine: A1 ========================="""
    },
    {
        "template_key": "heat_bed_hotend",
        "name": "Heat Bed & Hotend",
        "description": "Start heating heatbed and hotend to initial temperatures",
        "category": "start",
        "order": 2,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start to heat heatbead&hotend==========
M1002 gcode_claim_action : 2
M1002 set_filament_type:{filament_type}
M104 S140
M140 S{bed_temp}
;===== end to heat heatbead&hotend=========="""
    },
    {
        "template_key": "startup_sound",
        "name": "Startup Sound",
        "description": "Play startup melody when print begins",
        "category": "start",
        "order": 3,
        "enabled": True,
        "controllable": True,
        "setting_key": "startup_sound",
        "gcode": """;=====start printer sound ===================
M17
M400 S1
M1006 S1
M1006 A0 B10 L100 C37 D10 M60 E37 F10 N60
M1006 A0 B10 L100 C41 D10 M60 E41 F10 N60
M1006 A0 B10 L100 C44 D10 M60 E44 F10 N60
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N60
M1006 A43 B10 L100 C46 D10 M70 E39 F10 N80
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N80
M1006 A0 B10 L100 C43 D10 M60 E39 F10 N80
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N80
M1006 A0 B10 L100 C41 D10 M80 E41 F10 N80
M1006 A0 B10 L100 C44 D10 M80 E44 F10 N80
M1006 A0 B10 L100 C49 D10 M80 E49 F10 N80
M1006 A0 B10 L100 C0 D10 M80 E0 F10 N80
M1006 A44 B10 L100 C48 D10 M60 E39 F10 N80
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N80
M1006 A0 B10 L100 C44 D10 M80 E39 F10 N80
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N80
M1006 A43 B10 L100 C46 D10 M60 E39 F10 N80
M1006 W
M18 
;=====end  printer sound end ==================="""
    },
    {
        "template_key": "avoid_end_stop",
        "name": "Avoid End Stop",
        "description": "Move Z axis to avoid end stop issues",
        "category": "start",
        "order": 4,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start avoid end stop =================
G91
G380 S2 Z40 F1200
G380 S3 Z-15 F1200
G90
;=====end avoid end stop ================="""
    },
    {
        "template_key": "reset_machine_status",
        "name": "Reset Machine Status",
        "description": "Reset motor currents, feedrate, flowrate and machine status",
        "category": "start",
        "order": 5,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start reset machine status =================
M204 S6000

M630 S0 P0
G91
M17 Z0.3 ; lower the z-motor current

G90
M17 X0.65 Y1.2 Z0.6 ; reset motor current to default
M960 S5 P1 ; turn on logo lamp
G90
M220 S100 ;Reset Feedrate
M221 S100 ;Reset Flowrate
M73.2   R1.0 ;Reset left time magnitude
;===== end reset machine status ================="""
    },
    {
        "template_key": "cog_noise_reduction",
        "name": "Cog Noise Reduction",
        "description": "Home X, extrude test, home Z with cog noise reduction",
        "category": "start",
        "order": 6,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;====== start cog noise reduction=================
M982.2 S1 ; turn on cog noise reduction

M1002 gcode_claim_action : 13

G28 X
G91
G1 Z5 F1200
G90
G0 X128 F30000
G0 Y254 F3000
G91
G1 Z-5 F1200

M109 S25 H140

M17 E0.3
M83
G1 E10 F1200
G1 E-0.5 F30
M17 D

G28 Z P0 T140; home z with low precision,permit 300deg temperature
M104 S{nozzle_temp}

M1002 judge_flag build_plate_detect_flag
M622 S1
  G39.4
  G90
  G1 Z5 F1200
M623
;====== end cog noise reduction================="""
    },
    {
        "template_key": "prepare_material",
        "name": "Prepare Print Temperature & Material",
        "description": "Load filament from AMS, flush and prepare material",
        "category": "start",
        "order": 7,
        "enabled": True,
        "controllable": True,
        "setting_key": "ams_slot",
        "gcode": """;===== start prepare print temperature and material ==========
M1002 gcode_claim_action : 24

M400
M211 X0 Y0 Z0 ;turn off soft endstop
M975 S1 ; turn on

G90
G1 X-28.5 F30000
G1 X-48.2 F3000

M620 M ;enable remap
M620 S{ams_slot}A   ; switch material if AMS exist
    ; Check if filament already loaded - skip change if same slot
    M622 J{filament_already_loaded}
        ; Filament already loaded, just set temperature
        M109 S{nozzle_temp}
        M1002 set_filament_type:{filament_type}
    M623
    M622 J0
        ; Filament not loaded, do full change sequence
        M1002 gcode_claim_action : 4
        M400
        M1002 set_filament_type:UNKNOWN
        M109 S{nozzle_temp}
        M104 S250
        M400
        T{ams_slot}
        G1 X-48.2 F3000
        M400

        M620.1 E F{flush_speed} T{flush_temp}
        M109 S250 ;set nozzle to common flush temp
        M106 P1 S0
        G92 E0
        G1 E50 F200
        M400
        M1002 set_filament_type:{filament_type}
    M623
M621 S{ams_slot}A

; Skip flush if filament already loaded
M622 J{filament_already_loaded}
M623
M622 J0
    M109 S{flush_temp} H300
    G92 E0
    G1 E50 F200 ; lower extrusion speed to avoid clog
    M400
    M106 P1 S178
    G92 E0
    G1 E5 F200
    M104 S{nozzle_temp}
    G92 E0
    G1 E-0.5 F300

    G1 X-28.5 F30000
    G1 X-48.2 F3000
    G1 X-28.5 F30000 ;wipe and shake
    G1 X-48.2 F3000
    G1 X-28.5 F30000 ;wipe and shake
    G1 X-48.2 F3000
M623

M400
M106 P1 S0
;===== end prepare print temperature and material end ====="""
    },
    {
        "template_key": "flow_calibration",
        "name": "Auto Extrude Calibration",
        "description": "Automatic extrusion calibration for flow accuracy",
        "category": "start",
        "order": 8,
        "enabled": True,
        "controllable": True,
        "setting_key": "flow_calibration",
        "gcode": """;===== start auto extrude cali start =========================
M975 S1

G90
M83
T1000
G1 X-48.2 Y0 Z10 F10000
M400
M1002 set_filament_type:UNKNOWN

M412 S1 ;  ===turn on  filament runout detection===
M400 P10
M620.3 W1; === turn on filament tangle detection===
M400 S2

M1002 set_filament_type:{filament_type}

M1002 judge_flag extrude_cali_flag

M622 J1
    M1002 gcode_claim_action : 8

    M109 S{nozzle_temp}
    G1 E10 F{max_volumetric_speed}
    M983 F{max_volumetric_speed} A0.3 H0.4; cali dynamic extrusion compensation

    M106 P1 S255
    M400 S5
    G1 X-28.5 F18000
    G1 X-48.2 F3000
    G1 X-28.5 F18000 ;wipe and shake
    G1 X-48.2 F3000
    G1 X-28.5 F12000 ;wipe and shake
    G1 X-48.2 F3000
    M400
    M106 P1 S0

    M1002 judge_last_extrude_cali_success
    M622 J0
        M983 F{max_volumetric_speed} A0.3 H0.4; cali dynamic extrusion compensation
        M106 P1 S255
        M400 S5
        G1 X-28.5 F18000
        G1 X-48.2 F3000
        G1 X-28.5 F18000 ;wipe and shake
        G1 X-48.2 F3000
        G1 X-28.5 F12000 ;wipe and shake
        M400
        M106 P1 S0
    M623
    
    G1 X-48.2 F3000
    M400
    M984 A0.1 E1 S1 F{max_volumetric_speed} H0.4
    M106 P1 S178
    M400 S7
    G1 X-28.5 F18000
    G1 X-48.2 F3000
    G1 X-28.5 F18000 ;wipe and shake
    G1 X-48.2 F3000
    G1 X-28.5 F12000 ;wipe and shake
    G1 X-48.2 F3000
    M400
    M106 P1 S0
M623 ; end of "draw extrinsic para cali paint"

M104 S170 ; prepare to wipe nozzle
M106 S255 ; turn on fan
;===== end auto extrude cali end ========================"""
    },
    {
        "template_key": "vibration_test",
        "name": "Mech Mode Fast Check (Vibration Test)",
        "description": "Quick vibration/resonance test for mechanical calibration",
        "category": "start",
        "order": 9,
        "enabled": False,
        "controllable": True,
        "setting_key": "vibration_test",
        "gcode": """;=====start  mech mode fast check start =====================
M1002 gcode_claim_action : 3

G1 X128 Y128 F20000
G1 Z5 F1200
M400 P200
M970.3 Q1 A5 K0 O3
M974 Q1 S2 P0

M970.2 Q1 K1 W58 Z0.1
M974 S2

G1 X128 Y128 F20000
G1 Z5 F1200
M400 P200
M970.3 Q0 A10 K0 O1
M974 Q0 S2 P0

M970.2 Q0 K1 W78 Z0.1
M974 S2

M975 S1
G1 F30000
G1 X0 Y5
G28 X ; re-home XY

G1 Z4 F1200
;=====end mech mode fast check end ======================="""
    },
    {
        "template_key": "wipe_nozzle",
        "name": "Wipe Nozzle",
        "description": "Clean nozzle by touching and wiping on steel surface",
        "category": "start",
        "order": 10,
        "enabled": True,
        "controllable": True,
        "setting_key": "wipe_nozzle",
        "gcode": """;===== start wipe nozzle ===============================
M1002 gcode_claim_action : 14

M975 S1
M106 S255 ; turn on fan (G28 has turn off fan)
M211 S; push soft endstop status
M211 X0 Y0 Z0 ;turn off Z axis endstop

;===== start remove waste by touching start =====

M104 S170 ; set temp down to heatbed acceptable

M83
G1 E-1 F500
G90
M83

M109 S170
G0 X108 Y-0.5 F30000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X110 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X112 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X114 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X116 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X118 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X120 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X122 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X124 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X126 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X128 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X130 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X132 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X134 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X136 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X138 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X140 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X142 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X144 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X146 F10000
G380 S3 Z-5 F1200
G1 Z2 F1200
G1 X148 F10000
G380 S3 Z-5 F1200

G1 Z5 F30000
;===== end remove waste by touching end =====
;===== end wipe nozzle ==============================="""
    },
    {
        "template_key": "clean_nozzle",
        "name": "Clean Nozzle",
        "description": "Deep clean nozzle on exposed steel surface with circular motion",
        "category": "start",
        "order": 11,
        "enabled": True,
        "controllable": True,
        "setting_key": "clean_nozzle",
        "gcode": """;===== start clean nozzle =====
G1 Z10 F1200
G0 X118 Y261 F30000
G1 Z5 F1200
M109 S{nozzle_temp_minus_50}

G28 Z P0 T300; home z with low precision,permit 300deg temperature
G29.2 S0 ; turn off ABL
M104 S140 ; prepare to abl
G0 Z5 F20000

G0 X128 Y261 F20000  ; move to exposed steel surface
G0 Z-1.01 F1200      ; stop the nozzle

G91
G2 I1 J0 X2 Y0 F2000.1
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5

G90
G1 Z10 F1200
;===== end clean nozzle ====="""
    },
    {
        "template_key": "brush_wipe",
        "name": "Brush Material Wipe",
        "description": "Wipe nozzle using brush material back and forth",
        "category": "start",
        "order": 12,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start brush material wipe nozzle =====

G90
G1 Y250 F30000
G1 X55
G1 Z1.300 F1200
G1 Y262.5 F6000
G91
G1 X-35 F30000
G1 Y-0.5
G1 X45
G1 Y-0.5
G1 X-45
G1 Y-0.5
G1 X45
G1 Y-0.5
G1 X-45
G1 Y-0.5
G1 X45
G1 Z5.000 F1200

G90
G1 X30 Y250.000 F30000
G1 Z1.300 F1200
G1 Y262.5 F6000
G91
G1 X35 F30000
G1 Y-0.5
G1 X-45
G1 Y-0.5
G1 X45
G1 Y-0.5
G1 X-45
G1 Y-0.5
G1 X45
G1 Y-0.5
G1 X-45
G1 Z10.000 F1200

;===== end brush material wipe nozzle end ====="""
    },
    {
        "template_key": "final_wipe",
        "name": "Final Wipe Nozzle",
        "description": "Final nozzle wipe with circular motion on steel surface",
        "category": "start",
        "order": 13,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start wipe nozzle start ================================
G90
G1 Y250 F30000
G1 X138
G1 Y261
G0 Z-1.01 F1200      ; stop the nozzle

G91
G2 I1 J0 X2 Y0 F2000.1
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5
G2 I1 J0 X2
G2 I-0.75 J0 X-1.5

M109 S140
M106 S255 ; turn on fan (G28 has turn off fan)

M211 R; pop softend status
;===== end wipe nozzle end ================================"""
    },
    {
        "template_key": "auto_bed_leveling",
        "name": "Bed Leveling",
        "description": "Automatic bed leveling with G29",
        "category": "start",
        "order": 14,
        "enabled": True,
        "controllable": True,
        "setting_key": "auto_bed_leveling",
        "gcode": """;===== start bed leveling ==================================
M1002 judge_flag g29_before_print_flag

G90
G1 Z5 F1200
G1 X0 Y0 F30000
G29.2 S1 ; turn on ABL

M190 S{bed_temp}; ensure bed temp
M109 S140
M106 S0 ; turn off fan , too noisy

M622 J1
    M1002 gcode_claim_action : 1
    G29 A1 X0 Y0 I256 J256
    M400
    M500 ; save cali data
M623
;===== end bed leveling end ================================"""
    },
    {
        "template_key": "home_after_wipe",
        "name": "Home After Wipe",
        "description": "Re-home XY after nozzle wipe if no ABL",
        "category": "start",
        "order": 15,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start home after wipe mouth============================
M1002 judge_flag g29_before_print_flag
M622 J0

    M1002 gcode_claim_action : 13
    G28

M623
;===== end home after wipe mouth end ======================="""
    },
    {
        "template_key": "prepare_print",
        "name": "Prepare Print",
        "description": "Final preparation before print starts",
        "category": "start",
        "order": 16,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start prepare =======================
G1 X108.000 Y-0.500 F30000
G1 Z0.300 F1200
M400
G2814 Z0.32

M104 S{nozzle_temp} ; prepare to print
;===== end prepare ======================="""
    },
    {
        "template_key": "nozzle_load_line",
        "name": "Nozzle Load Line",
        "description": "Draw purge line at front of bed before print",
        "category": "start",
        "order": 17,
        "enabled": False,
        "controllable": True,
        "setting_key": "nozzle_load_line",
        "gcode": """;===== start nozzle load line ===============================
G90
M83
G1 Z5 F1200
G1 X88 Y-0.5 F20000
G1 Z0.3 F1200

M109 S{nozzle_temp}

G1 E2 F300
G1 X168 E4.989 F6000
G1 Z1 F1200
;===== end nozzle load line end ==========================="""
    },
    {
        "template_key": "extrude_cali_test",
        "name": "Extrude Calibration Test",
        "description": "Test extrusion with calibration pattern",
        "category": "start",
        "order": 18,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start extrude cali test ===============================

M400
    M900 S
    M900 C
    G90
    M83

    M109 S{nozzle_temp}
    G0 X128 E8  F400
    G0 X133 E.3742  F100
    G0 X138 E.3742  F400
    G0 X143 E.3742  F100
    G0 X148 E.3742  F400
    G0 X153 E.3742  F100
    G91
    G1 X1 Z-0.300
    G1 X4
    G1 Z1 F1200
    G90
    M400

M900 R

M1002 judge_flag extrude_cali_flag
M622 J1
    G90
    G1 X108.000 Y1.000 F30000
    G91
    G1 Z-0.700 F1200
    G90
    M83
    G0 X128 E10  F400
    G0 X133 E.3742  F100
    G0 X138 E.3742  F400
    G0 X143 E.3742  F100
    G0 X148 E.3742  F400
    G0 X153 E.3742  F100
    G91
    G1 X1 Z-0.300
    G1 X4
    G1 Z1 F1200
    G90
    M400
M623

G1 Z0.2
;===== end extrude cali test ==============================="""
    },
    {
        "template_key": "turn_off_light",
        "name": "Turn Off Light & Wait",
        "description": "Turn off light and wait for extrude temperature",
        "category": "start",
        "order": 19,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;========start turn off light and wait extrude temperature =============
M1002 gcode_claim_action : 0
M400
;========end  turn off light and wait extrude temperature ============="""
    },
    {
        "template_key": "final_start",
        "name": "Final Start",
        "description": "Final settings before print layers begin",
        "category": "start",
        "order": 20,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start final ==
M960 S1 P0 ; turn off laser
M960 S2 P0 ; turn off laser
M106 S0 ; turn off fan
M106 P2 S0 ; turn off big fan
M106 P3 S0 ; turn off chamber fan

M975 S1 ; turn on mech mode supression
G90
M83
T1000

M211 X0 Y0 Z0 ;turn off soft endstop
M1007 S1 ; turn on mass estimation
G29.4
;===== end final =="""
    },
    {
        "template_key": "pre_extrude",
        "name": "Pre-Extrude",
        "description": "Extrude a little before print start to fill nozzle",
        "category": "start",
        "order": 21,
        "enabled": True,
        "controllable": True,
        "setting_key": "pre_extrude",
        "gcode": """;===== start pre-extrude ==
G0 E{pre_extrude_length} F800 ; Extrude a little so nozzle is filled for print start
M104 S{nozzle_temp} ; heat up to full temp in first few moves
;===== end pre-extrude =="""
    },
    
    # ===== END SEQUENCE =====
    {
        "template_key": "end_print_start",
        "name": "End Print Start",
        "description": "Begin end sequence, turn off heaters and fans",
        "category": "end",
        "order": 1,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start end print sequence =====
M400 ; wait for buffer to clear
G92 E0 ; zero the extruder
G1 E-0.5 F300 ; retract filament
M104 S0 ; turn off hotend
M140 S0 ; turn off heatbed
M106 S0 ; turn off part cooling fan
M106 P2 S0 ; turn off aux fan
M106 P3 S0 ; turn off chamber fan
;===== end start end print sequence ====="""
    },
    {
        "template_key": "timelapse",
        "name": "Timelapse Capture",
        "description": "Capture final timelapse frames",
        "category": "end",
        "order": 2,
        "enabled": False,
        "controllable": True,
        "setting_key": "timelapse",
        "gcode": """;===== start timelapse capture =====
M1002 judge_flag timelapse_record_flag
M622 J1
    M400 P100
    M971 S11 C11 O0
    M971 S11 C11 O0
    M971 S11 C11 O0
    M991 S0 P-1 ; end timelapse
M623
;===== end timelapse capture ====="""
    },
    {
        "template_key": "move_to_safe",
        "name": "Move to Safe Position",
        "description": "Raise Z and move to safe position",
        "category": "end",
        "order": 3,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start move to safe position =====
G91 ; relative positioning
G1 Z5 F1200 ; raise Z by 5mm
G90 ; absolute positioning
G1 X0 Y250 F12000 ; move to back corner
;===== end move to safe position ====="""
    },
    {
        "template_key": "auto_eject",
        "name": "Auto Eject",
        "description": "Auto push-off print from bed after cooling",
        "category": "end",
        "order": 4,
        "enabled": False,
        "controllable": True,
        "setting_key": "auto_eject",
        "gcode": """;===== start auto eject =====
; Wait for bed to cool down before eject
M190 S{cooldown_temp} ; wait for bed to cool to target temp
G1 Y128 F12000 ; move to center Y
G1 X128 F12000 ; move to center
M400 ; wait for moves to complete
G1 Y260 F3000 ; push print off
G1 Y128 F12000 ; return to center
G1 X0 Y250 F12000 ; move to back corner
;===== end auto eject ====="""
    },
    {
        "template_key": "end_sound",
        "name": "End Sound",
        "description": "Play completion melody",
        "category": "end",
        "order": 5,
        "enabled": True,
        "controllable": True,
        "setting_key": "end_sound",
        "gcode": """;===== start end sound =====
M17
M400 S1
M1006 S1
M1006 A0 B10 L100 C49 D10 M60 E49 F10 N60
M1006 A0 B10 L100 C44 D10 M60 E44 F10 N60
M1006 A0 B10 L100 C41 D10 M60 E41 F10 N60
M1006 A0 B10 L100 C37 D10 M60 E37 F10 N60
M1006 W
M18
;===== end end sound ====="""
    },
    {
        "template_key": "end_print_final",
        "name": "End Print Final",
        "description": "Final cleanup, turn off motors and lights",
        "category": "end",
        "order": 6,
        "enabled": True,
        "controllable": False,
        "setting_key": None,
        "gcode": """;===== start end print final =====
M400 ; wait for buffer to clear
M18 X Y ; turn off X and Y steppers
M960 S5 P0 ; turn off logo lamp
M1002 gcode_claim_action : 0
;===== end end print final ====="""
    },
]


def run_migration():
    """Delete all old templates and insert new ones"""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Delete all existing templates
        cursor.execute("DELETE FROM gcode_templates")
        print(f"Deleted all existing templates")
        
        # Insert new templates
        for template in NEW_TEMPLATES:
            cursor.execute("""
                INSERT INTO gcode_templates 
                (template_key, name, description, category, "order", enabled, controllable, setting_key, gcode, printer_model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """, (
                template["template_key"],
                template["name"],
                template["description"],
                template["category"],
                template["order"],
                1 if template["enabled"] else 0,
                1 if template["controllable"] else 0,
                template["setting_key"],
                template["gcode"],
            ))
            print(f"  + {template['category']}/{template['order']:02d}: {template['name']}")
        
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM gcode_templates WHERE category='start'")
        start_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM gcode_templates WHERE category='end'")
        end_count = cursor.fetchone()[0]
        
        print(f"\n✅ Migration complete!")
        print(f"   Start templates: {start_count}")
        print(f"   End templates: {end_count}")
        print(f"   Total: {start_count + end_count}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
