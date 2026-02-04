# AMS Auto-Sync Mechanism

## 📋 Overview

Dokumen ini menjelaskan bagaimana sistem kita melakukan sync data AMS dari printer ke database, terinspirasi dari implementasi OrcaSlicer/BambuStudio.

## 🎯 Problem Statement

**Current Behavior:**
- ✅ AMS data ditangkap dari MQTT real-time
- ✅ Data disimpan di memory (dalam `bambu_service.py`)
- ❌ Database slot assignments **TIDAK auto-sync** dengan printer
- ❌ Saat frontend dibuka, data di database mungkin **outdated**

**User Expectation (Seperti OrcaSlicer):**
- Saat buka aplikasi → Tampilkan data AMS **sesuai kondisi real printer**
- Saat ganti filament di printer → Database **auto-update**
- Saat lepas/pasang tray → Database **sinkron otomatis**

## 🔍 How OrcaSlicer Does It

### 1. **Continuous MQTT Monitoring**
```cpp
// DeviceManager.cpp Line 3367
int MachineObject::parse_json(std::string payload)
{
    if (jj.contains("ams_filament_setting")) {
        // Auto-update tray info from MQTT
        tray->m_fila_type = setting_id_to_type(...);
        tray->set_hold_count(); // Prevent rapid updates
    }
}
```

### 2. **Detect Tray Changes**
```cpp
// StatusPanel.cpp Line 3345
void StatusPanel::update_ams(MachineObject *obj)
{
    // Sync when tray existence bits change
    if (last_tray_exist_bits != obj->tray_exist_bits) {
        UpdateAms(); // Re-sync all
        last_tray_exist_bits = obj->tray_exist_bits;
    }
}
```

### 3. **Sync On Connection**
```cpp
// SyncAmsInfoDialog.cpp Line 2227
void SyncAmsInfoDialog::on_timer(wxTimerEvent &event)
{
    if (!m_check_flag && obj_->is_info_ready()) {
        update_select_layout(obj_); // Initial sync
        m_check_flag = true;
    }
}
```

## 🛠️ Our Implementation Strategy

### **Option 1: Auto-Sync dari MQTT Handler** (RECOMMENDED)

**Kapan:** Setiap kali `_process_ams_data()` dipanggil
**Dimana:** `src/services/bambu_service.py` Line ~900

```python
def _process_ams_data(self, ams_data: Dict[str, Any]):
    # ... existing parsing code ...
    
    # NEW: Auto-sync to database
    if self._should_sync_to_database():
        self._sync_ams_to_database()
```

**Advantages:**
- ✅ Real-time sync
- ✅ Selalu up-to-date
- ✅ No manual trigger needed

**Disadvantages:**
- ❌ Banyak write ke database (every 5 seconds)
- ❌ Performance overhead

### **Option 2: Smart Sync (Change Detection)** (BALANCED ⭐)

**Kapan:** Hanya saat `tray_exist_bits` berubah
**Dimana:** `src/services/bambu_service.py` Line ~900

```python
def _process_ams_data(self, ams_data: Dict[str, Any]):
    # Detect changes
    old_tray_bits = self.ams_data.get("tray_exist_bits", "0")
    new_tray_bits = ams_data.get("tray_exist_bits", "0")
    
    if old_tray_bits != new_tray_bits:
        logger.info(f"🔄 AMS tray changed: {old_tray_bits} → {new_tray_bits}")
        self._sync_ams_to_database()
    
    # ... existing parsing code ...
```

**Advantages:**
- ✅ Minimal database writes
- ✅ Sync saat user ganti filament
- ✅ Good balance performance vs accuracy

**Disadvantages:**
- ⚠️ Tidak sync jika hanya `remain` yang berubah

### **Option 3: API Endpoint Trigger** (MANUAL)

**Kapan:** Frontend request manual sync
**Dimana:** New API endpoint

```python
@router.post("/api/printers/{printer_id}/ams/sync")
async def sync_ams_from_printer(printer_id: str):
    """Manually trigger AMS sync from printer to database"""
    bambu_service.sync_ams_to_database()
    return {"status": "synced"}
```

**Advantages:**
- ✅ User control
- ✅ No automatic overhead
- ✅ Clear trigger point

**Disadvantages:**
- ❌ User harus manually trigger
- ❌ Tidak real-time

## 🚀 Recommended Implementation

**Hybrid Approach:**

1. **Smart Auto-Sync** (Option 2) - Background sync saat detect changes
2. **Manual Sync Button** (Option 3) - User dapat force sync
3. **On Connect Sync** - Initial sync saat printer online

### Implementation Code:

#### 1. Add to `bambu_service.py`:

```python
class BambuLabMQTTClient:
    def __init__(self, ...):
        # ... existing code ...
        self._last_tray_exist_bits = "0"  # Track changes
    
    def _process_ams_data(self, ams_data: Dict[str, Any]):
        """Process AMS data with auto-sync"""
        try:
            # Detect tray changes
            old_bits = self._last_tray_exist_bits
            new_bits = ams_data.get("tray_exist_bits", "0")
            
            # ... existing parsing code ...
            
            # Auto-sync if trays changed
            if old_bits != new_bits:
                logger.info(f"🔄 AMS trays changed: {old_bits} → {new_bits}, syncing to DB...")
                asyncio.create_task(self._sync_ams_to_database())
                self._last_tray_exist_bits = new_bits
                
        except Exception as e:
            logger.error(f"Error in AMS processing: {e}")
    
    async def _sync_ams_to_database(self):
        """Sync current AMS data to database slot assignments"""
        from src.database import SessionLocal
        from src.database.db import AMSSlotAssignment, FilamentProfile
        
        db = SessionLocal()
        try:
            # Get current AMS data from memory
            ams_list = self.ams_data.get("ams", [])
            
            for ams_unit in ams_list:
                for tray in ams_unit.get("trays", []):
                    if tray.get("empty", True):
                        continue  # Skip empty slots
                    
                    slot_number = tray.get("id", 0)
                    tray_type = tray.get("type", "")
                    tray_color = tray.get("color", "")
                    
                    # Find or create matching filament profile
                    # (Implementation depends on your filament matching logic)
                    
                    # Update or create slot assignment
                    assignment = db.query(AMSSlotAssignment).filter(
                        AMSSlotAssignment.printer_id == self.printer_id,
                        AMSSlotAssignment.slot_number == slot_number
                    ).first()
                    
                    if assignment:
                        # Update existing
                        assignment.remaining_grams = tray.get("remain", 0) * 10  # Convert % to grams
                        logger.info(f"✅ Updated slot {slot_number}: {tray_type}, {assignment.remaining_grams}g")
                    # else: Create new assignment (if you want auto-creation)
                    
            db.commit()
            logger.info("✅ AMS database sync complete")
            
        except Exception as e:
            logger.error(f"❌ AMS database sync failed: {e}")
            db.rollback()
        finally:
            db.close()
```

#### 2. Add API Endpoint (`src/api/ams.py`):

```python
@router.post("/api/printers/{printer_id}/ams/sync-from-printer")
async def sync_ams_from_printer(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Manually sync AMS data from printer to database.
    Useful when user wants to refresh slot assignments.
    """
    bambu_client = print_service.get_bambu_client(printer_id)
    if not bambu_client:
        raise HTTPException(404, "Printer not found")
    
    await bambu_client._sync_ams_to_database()
    
    return {
        "status": "success",
        "message": "AMS data synced from printer to database"
    }
```

#### 3. Add Frontend Button (Dashboard.tsx):

```tsx
const handleSyncAmsFromPrinter = async () => {
  try {
    setLoading(true);
    await printFarmClient.syncAmsFromPrinter(printer.printerId);
    
    // Refresh assignments
    await loadSlotAssignments();
    
    toast.success('AMS data synced from printer!');
  } catch (err) {
    toast.error('Failed to sync AMS data');
  } finally {
    setLoading(false);
  }
};

// In UI:
<button onClick={handleSyncAmsFromPrinter}>
  🔄 Sync from Printer
</button>
```

## 📊 Sync Triggers Summary

| Trigger | Implementation | Frequency | Use Case |
|---------|---------------|-----------|----------|
| **On Connect** | `_on_connect()` | Once per connection | Initial sync saat printer online |
| **Tray Change** | `_process_ams_data()` | When `tray_exist_bits` changes | Auto-detect filament swap |
| **Manual Button** | API endpoint | On demand | User wants to refresh |
| **On Frontend Load** | (Optional) API call on mount | Once per page load | Ensure latest data |

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────┐
│  BAMBU PRINTER                          │
│  - Filament changed                     │
│  - Tray added/removed                   │
└──────────────┬──────────────────────────┘
               │ MQTT (every 5s)
               ▼
┌─────────────────────────────────────────┐
│  bambu_service.py                       │
│  - _process_ams_data()                  │
│  - Detect tray_exist_bits change        │
│  - TRIGGER: _sync_ams_to_database()     │
└──────────────┬──────────────────────────┘
               │ SQL UPDATE
               ▼
┌─────────────────────────────────────────┐
│  DATABASE (farm.db)                     │
│  - ams_slot_assignments                 │
│  - remaining_grams updated              │
└──────────────┬──────────────────────────┘
               │ API Request
               ▼
┌─────────────────────────────────────────┐
│  FRONTEND (AmsStatusDisplay)            │
│  - Display updated slot info            │
│  - Show current filaments               │
└─────────────────────────────────────────┘
```

## ⚠️ Important Considerations

### 1. **Filament Matching**
- Printer hanya kirim `tray_type` dan `tray_color`
- Database punya `filament_profiles` dengan detail lengkap
- **Challenge:** Bagaimana match "PLA" dari printer ke specific filament profile?

**Solutions:**
- Option A: Match by `material_type` + `color_hex` (fuzzy matching)
- Option B: User manually assign first time, then track by slot
- Option C: Create "Unknown PLA" profile auto jika tidak ada match

### 2. **Remaining Calculation**
- Printer kirim `remain` dalam **persen (0-100)**
- Database store `remaining_grams` dalam **grams**
- Need conversion: `remain_grams = (remain_percent / 100) * original_spool_weight`

**Challenge:** Kita tidak tahu original spool weight dari printer
**Solution:** Assume 1000g standard, atau store saat user assign

### 3. **Sync Conflicts**
- Jika user edit di frontend saat auto-sync berjalan?
- **Solution:** Timestamp-based conflict resolution atau lock mechanism

### 4. **Performance**
- Jangan sync terlalu sering (rate limiting)
- Batch updates instead of per-tray
- Use async/background tasks

## 🎯 Next Steps

1. ✅ Dokumen ini selesai
2. ⏭️ Implementasi Option 2 (Smart Sync)
3. ⏭️ Add manual sync button to frontend
4. ⏭️ Testing dengan real printer

---

**Last Updated:** 2026-02-02  
**Status:** Design Complete, Awaiting Implementation
