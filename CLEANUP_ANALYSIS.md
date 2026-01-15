# Analisis File untuk Cleanup

## 🎯 Kriteria Penghapusan
1. File tidak digunakan oleh production code (`src/`)
2. File tidak di-import oleh file lain
3. File adalah test/debug/development utility
4. Ada alternatif yang lebih baik

---

## ❌ File yang AMAN untuk Dihapus

### 1. Test Files yang Menggunakan HTTP Method (Deprecated)
**Status:** Test untuk metode lama yang sudah tidak dipakai

#### `tests/test_direct_print.py`
- ❌ Menggunakan `send_print_file()` (HTTP method) 
- ✅ Alternatif: `test_direct_upload.py` (uses FTPS)
- **Safe to delete:** YES

#### `tests/test_simple_start.py`
- ❌ Menggunakan `send_print_file()` dengan HTTP URL
- ✅ Alternatif: `test_direct_upload.py`, `test_simple_upload_print.py`
- **Safe to delete:** YES

#### `tests/test_start_print.py`
- ❌ Menggunakan `send_print_file()` (HTTP method)
- ✅ Alternatif: test files yang pakai FTPS
- **Safe to delete:** YES

---

### 2. Debug/Development Utility Files
**Status:** Tools untuk development/debugging, tidak dipakai di production

#### `debug_mqtt_live.py`
- Tujuan: Monitor MQTT messages real-time
- Digunakan: Manual debugging only
- **Safe to delete:** YES (keep if useful for debugging)

#### `debug_mqtt_compare.py`
- Tujuan: Compare MQTT messages
- **Safe to delete:** YES

#### `debug_mqtt_exact.py`
- Tujuan: Debug MQTT exact messages
- **Safe to delete:** YES

#### `debug_actual_files.py`
- Tujuan: Debug file operations
- **Safe to delete:** YES

---

### 3. Development/Migration Scripts (Already Run)
**Status:** One-time migration scripts

#### `migrate_*.py` (Root directory)
- `migrate_filament_already_loaded.py`
- `migrate_gcode_templates_v2.py`
- `migrate_queue_file_path.py`
- `migrate_quick_start.py`
- `migrate_templates_db.py`
- **Safe to delete:** YES (migrations already applied)

---

### 4. Utility Scripts (Redundant)
**Status:** Utility scripts yang fungsinya sudah ada di tempat lain

#### `send_to_printer.py`
- Tujuan: Send file to printer manually
- Sudah ada: API endpoint `/api/print-control/{printer_id}/start-next`
- **Safe to delete:** MAYBE (useful for manual testing)

#### `send_to_printer_simple.py`
- Duplicate of above, simpler version
- **Safe to delete:** MAYBE (useful for manual testing)

---

### 5. Analysis/Compare Scripts
**Status:** One-time analysis tools

#### `compare_3mf.py`
- **Safe to delete:** YES

#### `compare_3mf_detail.py`
- **Safe to delete:** YES

#### `compare_original_vs_processed.py`
- **Safe to delete:** YES

#### `analyze_output.py`
- **Safe to delete:** YES

---

### 6. Check/Inspect Scripts (Development)
**Status:** Manual inspection tools

#### `inspect_start.py`
- **Safe to delete:** MAYBE (useful for debugging)

#### `inspect_tmp.py`
- **Safe to delete:** YES

#### `check_*.py` (Root directory - various check scripts)
- `check_db_status.py`
- `check_inventory.py`
- `check_preset.py`
- `check_queue.py`
- `check_remaining.py`
- `check_status.py`
- `check_template.py`
- **Safe to delete:** MAYBE (useful for quick checks)

---

### 7. Test Files (Misc)
**Status:** Old test files

#### `test_project_file_MOVED.py`
- Name indicates already moved
- **Safe to delete:** YES

#### `verify_queue_file.py`
- One-time verification
- **Safe to delete:** YES

---

## ✅ File yang HARUS DIPERTAHANKAN

### Production Code
- Semua file di `src/` directory
- `frontend/` directory
- `docs/` directory

### Configuration
- `.env`, `.env.example`
- `requirements.txt`
- `pytest.ini`

### Scripts yang Masih Berguna
- `scripts/` directory (utility scripts)
- `add_my_inventory.py` (if still used)
- `list_templates.py`
- `live_status.py`
- `process_3mf.py`
- `update_quick_print.py`

### Batch/Shell Files
- `start-*.bat`
- `run-*.bat`
- `start.sh`

### Test Infrastructure
- `tests/conftest.py`
- `tests/__init__.py`
- Active test files using FTPS method

---

## 📊 Rekomendasi Penghapusan (Prioritas)

### Priority 1: Hapus Sekarang (Aman 100%)
```
tests/test_direct_print.py
tests/test_simple_start.py
tests/test_start_print.py
test_project_file_MOVED.py
compare_3mf.py
compare_3mf_detail.py
compare_original_vs_processed.py
analyze_output.py
inspect_tmp.py
verify_queue_file.py
migrate_filament_already_loaded.py
migrate_gcode_templates_v2.py
migrate_queue_file_path.py
migrate_quick_start.py
migrate_templates_db.py
```

### Priority 2: Pertimbangkan Hapus (Berguna untuk Debugging)
```
debug_mqtt_live.py
debug_mqtt_compare.py
debug_mqtt_exact.py
debug_actual_files.py
send_to_printer.py
send_to_printer_simple.py
inspect_start.py
```

### Priority 3: Keep untuk Quick Checks
```
check_*.py files (useful untuk manual inspection)
live_status.py
```

---

## 🔧 Function Deprecation

### `bambu_service.py`
- `send_print_file()` function (line 1960-2070)
  - **Status:** Legacy, not used in production
  - **Action:** Add deprecation warning or remove
  - **Used by:** Only test files marked for deletion

---

## 📝 Total Impact
- **Test files to delete:** 3-4 files
- **Debug files to delete:** 4 files  
- **Migration files to delete:** 5 files
- **Analysis files to delete:** 4 files
- **Misc files to delete:** 2 files
- **Total:** ~18-22 files dapat dihapus dengan aman

**Storage saved:** ~50-100KB (minimal impact, mainly for code cleanliness)
