/**
 * AMS Status Display Component - With Slot Assignments
 * 
 * Features:
 * - Visual AMS display with 4 slots
 * - Shows filament name, brand, type from inventory
 * - Shows remaining grams (tracked in database)
 * - Stage 1: Select filament from inventory
 * - Stage 2: Detail view with Load/Unload and remaining input
 */
import React, { useState, useEffect, useCallback } from 'react';
import { printFarmClient } from '../api/client';

interface FilamentProfile {
  id: number;
  name: string;
  brand: string;
  materialType: string;
  colorHex: string;
  spoolWeight: number | null;
  nozzleTempDefault?: number;
  bedTempDefault?: number;
  isActive: boolean;
}

interface SlotAssignment {
  slot: number;
  filament_id: number;
  remaining_grams: number;
  name: string;
  brand: string;
  material_type: string;
  color_hex: string;
  color_name: string;
  nozzle_temp_default: number;
  bed_temp_default: number;
  spool_weight: number;
}

interface AmsTray {
  slot: number;
  name: string;
  type: string;
  color: string;
  remain: number;
  empty: boolean;
  is_external?: boolean;
}

interface AmsStatusData {
  printer_id: string;
  connected: boolean;
  tray_now: number;
  trays: AmsTray[];
}

interface AmsStatusDisplayProps {
  printerId: string;
  compact?: boolean;
}

type ModalStage = 'select' | 'detail';

export const AmsStatusDisplay: React.FC<AmsStatusDisplayProps> = ({ 
  printerId,
  compact = false 
}) => {
  const [amsData, setAmsData] = useState<AmsStatusData | null>(null);
  const [slotAssignments, setSlotAssignments] = useState<Record<number, SlotAssignment>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalStage, setModalStage] = useState<ModalStage>('select');
  const [editingSlot, setEditingSlot] = useState<number | null>(null);
  const [selectedFilament, setSelectedFilament] = useState<FilamentProfile | null>(null);
  
  // Inventory state
  const [inventory, setInventory] = useState<FilamentProfile[]>([]);
  const [loadingInventory, setLoadingInventory] = useState(false);
  
  // Action states
  const [applyingFilament, setApplyingFilament] = useState(false);
  const [loadingFilament, setLoadingFilament] = useState(false);
  const [unloadingFilament, setUnloadingFilament] = useState(false);
  const [syncingFromPrinter, setSyncingFromPrinter] = useState(false);
  
  // Loading progress tracking
  const [loadProgress, setLoadProgress] = useState<{
    active: boolean, 
    step: number, 
    isUnload: boolean,
    nozzleTemp: number,
    targetTemp: number,
    completed: boolean
  }>({
    active: false, step: 0, isUnload: false, nozzleTemp: 0, targetTemp: 220, completed: false
  });
  
  // Loading steps - matches printer display
  const LOAD_STEPS = [
    { name: 'Heat the Nozzle', showTemp: true },
    { name: 'Check filament location', showTemp: false },
    { name: 'Cut filament', showTemp: false },
    { name: 'Pull back current filament', showTemp: false },
    { name: 'Push new filament into the extruder', showTemp: false },
    { name: 'Purge old filament', showTemp: false }
  ];
  
  const UNLOAD_STEPS = [
    { name: 'Heat the Nozzle', showTemp: true },
    { name: 'Retract filament', showTemp: false },
    { name: 'Pull back filament', showTemp: false },
    { name: 'Complete', showTemp: false }
  ];

  const loadAmsStatus = useCallback(async () => {
    try {
      const data = await printFarmClient.getAmsTrays(printerId);
      setAmsData(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load AMS status:', err);
      setError('Failed to load AMS status');
    } finally {
      setLoading(false);
    }
  }, [printerId]);

  const loadSlotAssignments = useCallback(async () => {
    try {
      const data = await printFarmClient.getSlotAssignments(printerId);
      setSlotAssignments(data.slots || {});
    } catch (err) {
      console.error('Failed to load slot assignments:', err);
    }
  }, [printerId]);

  const loadInventory = useCallback(async () => {
    try {
      setLoadingInventory(true);
      const data = await printFarmClient.getAllFilaments();
      setInventory(data.filter((f: FilamentProfile) => f.isActive && (f.spoolWeight ?? 0) > 0));
    } catch (err) {
      console.error('Failed to load inventory:', err);
    } finally {
      setLoadingInventory(false);
    }
  }, []);

  useEffect(() => {
    loadAmsStatus();
    loadSlotAssignments();
    const interval = setInterval(() => {
      loadAmsStatus();
      loadSlotAssignments();
    }, 5000);
    return () => clearInterval(interval);
  }, [loadAmsStatus, loadSlotAssignments]);

  // Open modal - start at select stage
  const openModal = async (slot: number) => {
    setEditingSlot(slot);
    setModalStage('select');
    setSelectedFilament(null);
    setLoadProgress({ active: false, step: 0, isUnload: false, nozzleTemp: 0, targetTemp: 220, completed: false });
    setModalOpen(true);
    await loadInventory();
  };

  // Close modal
  const closeModal = () => {
    setModalOpen(false);
    setEditingSlot(null);
    setSelectedFilament(null);
    setModalStage('select');
    setLoadProgress({ active: false, step: 0, isUnload: false, nozzleTemp: 0, targetTemp: 220, completed: false });
  };

  // Select filament and assign to slot
  const selectFilament = async (filament: FilamentProfile) => {
    if (editingSlot === null) return;
    
    try {
      setApplyingFilament(true);
      
      // Assign filament to slot (this also sends to printer)
      await printFarmClient.assignFilamentToSlot(
        printerId, 
        editingSlot, 
        filament.id,
        filament.spoolWeight || 1000
      );
      
      // Set selected filament and go to detail stage
      setSelectedFilament(filament);
      setModalStage('detail');
      
      // Reload data
      setTimeout(() => {
        loadAmsStatus();
        loadSlotAssignments();
      }, 1000);
    } catch (err) {
      console.error('Failed to apply filament:', err);
      alert('Failed to apply filament to slot. Please try again.');
    } finally {
      setApplyingFilament(false);
    }
  };

  // Load filament from slot
  const handleLoad = async () => {
    if (editingSlot === null) return;
    
    try {
      setLoadingFilament(true);
      setLoadProgress({ 
        active: true, 
        step: 0, 
        isUnload: false, 
        nozzleTemp: 25, 
        targetTemp: 220,
        completed: false 
      });
      
      // Start actual load command
      printFarmClient.amsLoadFilament(printerId, editingSlot).catch(err => {
        console.error('Load command failed:', err);
      });
      
      // Poll real status from backend until complete
      let isComplete = false;
      let pollCount = 0;
      const maxPolls = 240; // 2 minutes max (240 * 500ms)
      
      while (!isComplete && pollCount < maxPolls) {
        await new Promise(resolve => setTimeout(resolve, 500));
        pollCount++;
        
        try {
          const status = await printFarmClient.getAmsLoadingStatus(printerId);
          
          // Update progress with real data from printer
          setLoadProgress({
            active: status.active || pollCount < 10, // Keep active for first 5 seconds even if backend says no
            step: status.current_step,
            isUnload: false,
            nozzleTemp: status.nozzle_temp || 25,
            targetTemp: status.target_temp || 220,
            completed: false
          });
          
          // Check if operation is complete
          // Complete when: ams_status is 768 (idle) AND we've been polling for a while
          if (status.completed || (!status.active && pollCount > 10)) {
            isComplete = true;
          }
        } catch (err) {
          console.error('Poll error:', err);
        }
      }
      
      // Mark as complete
      setLoadProgress(prev => ({ ...prev, completed: true }));
      
    } catch (err) {
      console.error('Failed to load filament:', err);
    } finally {
      setLoadingFilament(false);
    }
  };

  // Unload filament
  const handleUnload = async () => {
    try {
      setUnloadingFilament(true);
      setLoadProgress({ 
        active: true, 
        step: 0, 
        isUnload: true,
        nozzleTemp: 25,
        targetTemp: 220,
        completed: false
      });
      
      // Start actual unload command
      printFarmClient.amsUnloadFilament(printerId).catch(err => {
        console.error('Unload command failed:', err);
      });
      
      // Poll real status from backend until complete
      let isComplete = false;
      let pollCount = 0;
      const maxPolls = 240; // 2 minutes max
      
      while (!isComplete && pollCount < maxPolls) {
        await new Promise(resolve => setTimeout(resolve, 500));
        pollCount++;
        
        try {
          const status = await printFarmClient.getAmsLoadingStatus(printerId);
          
          // Update progress with real data from printer
          setLoadProgress({
            active: status.active || pollCount < 10,
            step: status.current_step,
            isUnload: true,
            nozzleTemp: status.nozzle_temp || 25,
            targetTemp: status.target_temp || 220,
            completed: false
          });
          
          // Check if operation is complete
          if (status.completed || (!status.active && pollCount > 10)) {
            isComplete = true;
          }
        } catch (err) {
          console.error('Poll error:', err);
        }
      }
      
      // Mark as complete
      setLoadProgress(prev => ({ ...prev, completed: true }));
      
    } catch (err) {
      console.error('Failed to unload filament:', err);
    } finally {
      setUnloadingFilament(false);
    }
  };
  
  // Cancel/Close progress
  const handleCancelProgress = () => {
    setLoadProgress({ active: false, step: 0, isUnload: false, nozzleTemp: 0, targetTemp: 220, completed: false });
  };

  // Go back to select stage
  const goBackToSelect = () => {
    setModalStage('select');
    setSelectedFilament(null);
    setLoadProgress({ active: false, step: 0, isUnload: false, nozzleTemp: 0, targetTemp: 220, completed: false });
  };

  // Sync AMS data from printer (inspired by OrcaSlicer)
  const handleSyncFromPrinter = async () => {
    try {
      setSyncingFromPrinter(true);
      const result = await printFarmClient.syncAmsFromPrinter(printerId);
      
      // Reload data after sync
      await loadSlotAssignments();
      
      console.log(`✅ Synced ${result.synced_slots} slots from printer at ${result.timestamp}`);
      alert(`✅ Synced ${result.synced_slots} slots from printer!`);
    } catch (err) {
      console.error('Failed to sync from printer:', err);
      alert('❌ Failed to sync AMS data from printer');
    } finally {
      setSyncingFromPrinter(false);
    }
  };

  // Parse color - ensure it always has # prefix
  const parseColor = (color: string): string => {
    if (!color || color === '' || color === '#000000' || color === '000000') return '#cccccc';
    if (color.startsWith('#')) {
      return color.length > 7 ? color.slice(0, 7) : color;
    }
    if (color.length >= 6) {
      return '#' + color.slice(0, 6);
    }
    return '#' + color;
  };

  // Check if color is light (needs dark outline for visibility)
  const isLightColor = (hexColor: string): boolean => {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    // Calculate relative luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.7; // Consider light if luminance > 70%
  };

  // Get slot display data - merge printer data with our assignments
  const getSlotDisplay = (slot: number, tray: AmsTray) => {
    const assignment = slotAssignments[slot];
    
    if (assignment && assignment.filament_id) {
      const color = parseColor(assignment.color_hex);
      // Calculate percentage: remaining_grams / 1000g (standard spool) * 100
      const spoolBase = 1000; // Always use 1kg as base for percentage
      const percent = Math.min(100, Math.round((assignment.remaining_grams / spoolBase) * 100));
      return {
        name: `${assignment.brand} ${assignment.material_type}`,
        type: assignment.material_type,
        color: color,
        remain: assignment.remaining_grams,
        remainPercent: percent,
        hasAssignment: true,
        brand: assignment.brand,
        fullName: assignment.name,
        isLight: isLightColor(color),
      };
    }
    
    // Fallback to printer data
    const color = parseColor(tray.color);
    return {
      name: tray.type || 'Unknown',
      type: tray.type,
      color: color,
      remain: 0,
      remainPercent: tray.remain,
      hasAssignment: false,
      brand: '',
      fullName: tray.name,
      isLight: isLightColor(color),
    };
  };

  if (loading) {
    return (
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        padding: '20px',
        textAlign: 'center',
      }}>
        Loading AMS status...
      </div>
    );
  }

  if (error || !amsData) {
    return (
      <div style={{
        backgroundColor: '#fef2f2',
        borderRadius: '12px',
        border: '1px solid #fecaca',
        padding: '20px',
        textAlign: 'center',
        color: '#dc2626',
      }}>
        {error || 'No AMS data available'}
      </div>
    );
  }

  const amsTrays = amsData.trays.filter(t => !t.is_external);
  const externalSpool = amsData.trays.find(t => t.is_external);
  const currentTray = amsData.tray_now;
  
  // Check if external spool has filament loaded
  const hasExternalFilament = externalSpool && !externalSpool.empty;

  return (
    <div style={{
      backgroundColor: '#ffffff',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      padding: compact ? '12px' : '20px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
      }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
          AMS Lite
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* Sync from Printer Button */}
          <button
            onClick={handleSyncFromPrinter}
            disabled={syncingFromPrinter || !amsData.connected}
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              backgroundColor: syncingFromPrinter ? '#e5e7eb' : '#3b82f6',
              color: '#ffffff',
              border: 'none',
              fontSize: '12px',
              fontWeight: 500,
              cursor: syncingFromPrinter || !amsData.connected ? 'not-allowed' : 'pointer',
              opacity: syncingFromPrinter || !amsData.connected ? 0.6 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Sync AMS data from printer to database (like OrcaSlicer)"
          >
            {syncingFromPrinter ? '⏳' : '🔄'} Sync
          </button>
          
          {/* Connection Status Badge */}
          <span style={{
            padding: '4px 10px',
            borderRadius: '12px',
            backgroundColor: amsData.connected ? '#dcfce7' : '#fee2e2',
            color: amsData.connected ? '#166534' : '#dc2626',
            fontSize: '12px',
            fontWeight: 500,
          }}>
            {amsData.connected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </div>

      {/* 4 Slot Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '10px',
        marginBottom: '16px',
      }}>
        {amsTrays.slice(0, 4).map((tray) => {
          const isActive = currentTray === tray.slot;
          const display = getSlotDisplay(tray.slot, tray);
          
          return (
            <div
              key={tray.slot}
              style={{
                position: 'relative',
                borderRadius: '10px',
                overflow: 'hidden',
                border: isActive ? '3px solid #fbbf24' : '2px solid #e5e7eb',
                backgroundColor: '#f8fafc',
              }}
            >
              {/* COLOR BAR */}
              <div style={{
                height: '50px',
                backgroundColor: tray.empty ? '#d1d5db' : display.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
              }}>
                {/* Slot number */}
                <span style={{
                  position: 'absolute',
                  top: '4px',
                  left: '6px',
                  backgroundColor: 'rgba(255,255,255,0.9)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                  fontWeight: 700,
                }}>
                  {tray.slot + 1}
                </span>
                
                {/* Active indicator */}
                {isActive && (
                  <span style={{
                    position: 'absolute',
                    top: '4px',
                    right: '4px',
                    fontSize: '14px',
                  }}>
                    ▶
                  </span>
                )}
              </div>
              
              {/* Info section */}
              <div style={{ padding: '8px' }}>
                {/* Brand & Type */}
                <div style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  marginBottom: '2px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: display.hasAssignment ? '#1f2937' : '#6b7280',
                }}>
                  {tray.empty ? 'Empty' : display.name}
                </div>
                
                {/* Remaining - only show if not empty */}
                {!tray.empty && (
                  <div style={{
                    fontSize: '11px',
                    color: display.hasAssignment ? '#059669' : '#6b7280',
                    marginBottom: '6px',
                    fontWeight: display.hasAssignment ? 500 : 400,
                  }}>
                    {display.hasAssignment 
                      ? `${display.remain}g (${display.remainPercent}%)`
                      : `${display.remainPercent}% remain`
                    }
                  </div>
                )}
                
                {/* Show empty text without percentage */}
                {tray.empty && (
                  <div style={{
                    fontSize: '11px',
                    color: '#9ca3af',
                    marginBottom: '6px',
                  }}>
                    No filament
                  </div>
                )}
                
                {/* Edit button */}
                <button
                  onClick={() => openModal(tray.slot)}
                  style={{
                    width: '100%',
                    padding: '6px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    backgroundColor: '#ffffff',
                    fontSize: '11px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    color: '#374151',
                  }}
                >
                  ✏️ Edit
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Connection lines SVG */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginBottom: '8px',
        height: '70px',
      }}>
        <svg width="340" height="70" viewBox="0 0 340 70">
          {amsTrays.slice(0, 4).map((tray, index) => {
            const x = 50 + index * 80;
            const isActive = currentTray === tray.slot;
            const display = getSlotDisplay(tray.slot, tray);
            const strokeW = isActive ? 10 : 6;
            
            return (
              <g key={tray.slot}>
                {/* Dark outline for light colors */}
                {display.isLight && (
                  <>
                    <line
                      x1={x}
                      y1="8"
                      x2={x}
                      y2="33"
                      stroke="#374151"
                      strokeWidth={strokeW + 3}
                      strokeLinecap="round"
                    />
                    <path
                      d={`M ${x} 33 Q ${x} 53, 170 63`}
                      fill="none"
                      stroke="#374151"
                      strokeWidth={strokeW + 3}
                      strokeLinecap="round"
                    />
                  </>
                )}
                {/* Actual filament color */}
                <line
                  x1={x}
                  y1="8"
                  x2={x}
                  y2="33"
                  stroke={display.color}
                  strokeWidth={strokeW}
                  strokeLinecap="round"
                />
                <path
                  d={`M ${x} 33 Q ${x} 53, 170 63`}
                  fill="none"
                  stroke={display.color}
                  strokeWidth={strokeW}
                  strokeLinecap="round"
                />
              </g>
            );
          })}
          <circle
            cx="170"
            cy="55"
            r="8"
            fill={currentTray >= 0 && currentTray < 4 
              ? getSlotDisplay(currentTray, amsTrays[currentTray]).color
              : (currentTray === 254 || hasExternalFilament)
                ? (externalSpool?.color || '#fbbf24')
                : '#6b7280'
            }
            stroke="#1f2937"
            strokeWidth="3"
          />
        </svg>
      </div>

      {/* Extruder Status */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '50px',
          height: '50px',
          backgroundColor: '#fbbf24',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '26px',
          boxShadow: '0 4px 12px rgba(251, 191, 36, 0.4)',
        }}>
          🖨️
        </div>
        {/* Extruder filament info */}
        <div style={{
          backgroundColor: currentTray >= 0 && currentTray < 4 ? '#f0fdf4' : (currentTray === 254 || hasExternalFilament) ? '#fef3c7' : '#f3f4f6',
          borderRadius: '8px',
          padding: '8px 12px',
          border: `1px solid ${currentTray >= 0 && currentTray < 4 ? '#bbf7d0' : (currentTray === 254 || hasExternalFilament) ? '#fde68a' : '#e5e7eb'}`,
        }}>
          {currentTray >= 0 && currentTray < 4 ? (
            <>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                Extruder Active
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{
                  width: '14px',
                  height: '14px',
                  borderRadius: '3px',
                  backgroundColor: getSlotDisplay(currentTray, amsTrays[currentTray]).color,
                  border: getSlotDisplay(currentTray, amsTrays[currentTray]).isLight 
                    ? '1px solid #9ca3af' 
                    : '1px solid transparent',
                }} />
                <span style={{ fontSize: '12px', fontWeight: 600 }}>
                  Slot {currentTray + 1}: {getSlotDisplay(currentTray, amsTrays[currentTray]).name}
                </span>
              </div>
            </>
          ) : currentTray === 254 || hasExternalFilament ? (
            <>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                External Spool
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{
                  width: '14px',
                  height: '14px',
                  borderRadius: '3px',
                  backgroundColor: externalSpool?.color || '#9ca3af',
                  border: '1px solid rgba(0,0,0,0.1)',
                }} />
                <span style={{ fontSize: '12px', fontWeight: 600 }}>
                  {externalSpool?.name || 'External Filament'}
                </span>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '2px' }}>
                Extruder Status
              </div>
              <div style={{ fontSize: '12px', fontWeight: 500, color: '#6b7280' }}>
                No filament loaded
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal */}
      {modalOpen && editingSlot !== null && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            maxWidth: '450px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
          }}>
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {modalStage === 'detail' && (
                  <button
                    onClick={goBackToSelect}
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: '#f3f4f6',
                      fontSize: '16px',
                      cursor: 'pointer',
                    }}
                  >
                    ←
                  </button>
                )}
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
                  {modalStage === 'select' 
                    ? `Select Filament for Slot ${editingSlot + 1}`
                    : `Slot ${editingSlot + 1} - Filament Details`
                  }
                </h3>
              </div>
              <button
                onClick={closeModal}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: '#f3f4f6',
                  fontSize: '18px',
                  cursor: 'pointer',
                }}
              >
                ×
              </button>
            </div>

            {/* Stage 1: Select Filament */}
            {modalStage === 'select' && (
              <>
                {/* Current slot info */}
                {slotAssignments[editingSlot] && (
                  <div style={{
                    backgroundColor: '#f0fdf4',
                    borderRadius: '8px',
                    padding: '12px',
                    marginBottom: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    border: '1px solid #bbf7d0',
                  }}>
                    <div style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '8px',
                      backgroundColor: parseColor(slotAssignments[editingSlot].color_hex),
                      border: '2px solid rgba(0,0,0,0.1)',
                    }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>
                        {slotAssignments[editingSlot].brand} {slotAssignments[editingSlot].material_type}
                      </div>
                      <div style={{ fontSize: '12px', color: '#059669' }}>
                        {slotAssignments[editingSlot].remaining_grams}g remaining
                      </div>
                    </div>
                  </div>
                )}

                {/* Inventory List */}
                <div style={{ marginBottom: '12px', fontWeight: 600, fontSize: '14px' }}>
                  Select from Inventory:
                </div>
                
                {loadingInventory ? (
                  <div style={{ textAlign: 'center', padding: '20px' }}>Loading...</div>
                ) : inventory.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>
                    No filaments in inventory
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflow: 'auto' }}>
                    {inventory.map((filament) => {
                      const colorValue = filament.colorHex || '';
                      const displayColor = colorValue.startsWith('#') 
                        ? colorValue.slice(0, 7) 
                        : colorValue.length >= 6 
                          ? '#' + colorValue.slice(0, 6) 
                          : '#cccccc';
                      
                      return (
                        <button
                          key={filament.id}
                          onClick={() => selectFilament(filament)}
                          disabled={applyingFilament}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            padding: '12px',
                            borderRadius: '10px',
                            border: '1px solid #e5e7eb',
                            backgroundColor: '#ffffff',
                            cursor: applyingFilament ? 'not-allowed' : 'pointer',
                            textAlign: 'left',
                            opacity: applyingFilament ? 0.6 : 1,
                          }}
                        >
                          <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '8px',
                            backgroundColor: displayColor,
                            border: '2px solid rgba(0,0,0,0.15)',
                            flexShrink: 0,
                          }} />
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600, fontSize: '14px' }}>
                              {filament.brand} {filament.materialType}
                            </div>
                            <div style={{ fontSize: '12px', color: '#6b7280' }}>
                              {filament.name} • {filament.spoolWeight}g
                            </div>
                          </div>
                          <span style={{ color: '#3b82f6', fontSize: '18px' }}>→</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {/* Stage 2: Detail with Load/Unload */}
            {modalStage === 'detail' && selectedFilament && (
              <>
                {/* Selected Filament Info */}
                <div style={{
                  backgroundColor: '#f0fdf4',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '20px',
                  border: '1px solid #bbf7d0',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                      width: '60px',
                      height: '60px',
                      borderRadius: '12px',
                      backgroundColor: parseColor(selectedFilament.colorHex),
                      border: '3px solid rgba(0,0,0,0.15)',
                    }} />
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '16px', color: '#166534' }}>
                        ✓ Applied Successfully
                      </div>
                      <div style={{ fontSize: '14px', color: '#15803d' }}>
                        {selectedFilament.brand} {selectedFilament.materialType}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Loading Progress Display */}
                {loadProgress.active && (
                  <div style={{
                    backgroundColor: '#1f2937',
                    borderRadius: '12px',
                    padding: '20px',
                    marginBottom: '20px',
                    color: '#ffffff',
                  }}>
                    <div style={{
                      fontSize: '16px',
                      fontWeight: 700,
                      marginBottom: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🔄 {loadProgress.isUnload ? 'Unload Filament' : 'Load Filament'}
                      </span>
                      {loadProgress.completed && (
                        <span style={{
                          backgroundColor: '#22c55e',
                          padding: '4px 10px',
                          borderRadius: '12px',
                          fontSize: '12px',
                        }}>
                          ✓ Complete
                        </span>
                      )}
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {(loadProgress.isUnload ? UNLOAD_STEPS : LOAD_STEPS).map((step, index) => {
                        const isCurrentStep = index === loadProgress.step;
                        const isCompleted = index < loadProgress.step || loadProgress.completed;
                        
                        return (
                          <div
                            key={index}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              padding: '8px 12px',
                              borderRadius: '8px',
                              backgroundColor: isCurrentStep && !loadProgress.completed ? 'rgba(59, 130, 246, 0.3)' : 'transparent',
                              border: isCurrentStep && !loadProgress.completed ? '1px solid #3b82f6' : '1px solid transparent',
                            }}
                          >
                            <span style={{
                              width: '24px',
                              height: '24px',
                              borderRadius: '50%',
                              backgroundColor: isCompleted ? '#22c55e' : isCurrentStep ? '#3b82f6' : '#4b5563',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '12px',
                              fontWeight: 700,
                            }}>
                              {isCompleted ? '✓' : index + 1}
                            </span>
                            <span style={{
                              flex: 1,
                              fontSize: '13px',
                              color: isCurrentStep ? '#ffffff' : isCompleted ? '#9ca3af' : '#6b7280',
                              fontWeight: isCurrentStep ? 600 : 400,
                            }}>
                              {step.name}
                              {/* Show temperature on heating step */}
                              {step.showTemp && isCurrentStep && !loadProgress.completed && (
                                <span style={{ 
                                  marginLeft: '8px', 
                                  color: '#fbbf24',
                                  fontWeight: 700,
                                }}>
                                  ({loadProgress.nozzleTemp}°C → {loadProgress.targetTemp}°C)
                                </span>
                              )}
                            </span>
                            {isCurrentStep && !loadProgress.completed && (
                              <span style={{ fontSize: '12px', color: '#60a5fa' }}>
                                ⏳
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    
                    {/* Done / Retry / Cancel buttons */}
                    <div style={{ 
                      display: 'flex', 
                      gap: '10px', 
                      marginTop: '16px' 
                    }}>
                      {loadProgress.completed ? (
                        <>
                          <button
                            onClick={handleCancelProgress}
                            style={{
                              flex: 1,
                              padding: '12px',
                              borderRadius: '8px',
                              border: 'none',
                              backgroundColor: '#22c55e',
                              color: '#ffffff',
                              fontSize: '14px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            ✓ Done
                          </button>
                          <button
                            onClick={loadProgress.isUnload ? handleUnload : handleLoad}
                            style={{
                              flex: 1,
                              padding: '12px',
                              borderRadius: '8px',
                              border: '1px solid #6b7280',
                              backgroundColor: 'transparent',
                              color: '#ffffff',
                              fontSize: '14px',
                              fontWeight: 500,
                              cursor: 'pointer',
                            }}
                          >
                            ↻ Retry
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={handleCancelProgress}
                          style={{
                            flex: 1,
                            padding: '10px',
                            borderRadius: '8px',
                            border: '1px solid #dc2626',
                            backgroundColor: 'transparent',
                            color: '#f87171',
                            fontSize: '13px',
                            fontWeight: 500,
                            cursor: 'pointer',
                          }}
                        >
                          ✕ Cancel
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Load/Unload Buttons - only show when not loading */}
                {!loadProgress.active && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px',
                    marginBottom: '16px',
                  }}>
                    <button
                      onClick={handleLoad}
                      disabled={loadingFilament || unloadingFilament}
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        border: 'none',
                        backgroundColor: '#3b82f6',
                        color: '#ffffff',
                        fontSize: '14px',
                        fontWeight: 600,
                        cursor: loadingFilament || unloadingFilament ? 'not-allowed' : 'pointer',
                        opacity: loadingFilament || unloadingFilament ? 0.6 : 1,
                      }}
                    >
                      ⬇️ Load
                    </button>
                    
                    <button
                      onClick={handleUnload}
                      disabled={loadingFilament || unloadingFilament}
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        border: 'none',
                        backgroundColor: '#f97316',
                        color: '#ffffff',
                        fontSize: '14px',
                        fontWeight: 600,
                        cursor: loadingFilament || unloadingFilament ? 'not-allowed' : 'pointer',
                        opacity: loadingFilament || unloadingFilament ? 0.6 : 1,
                      }}
                    >
                      ⬆️ Unload
                    </button>
                  </div>
                )}

                {/* Select Another - only show when not loading */}
                {!loadProgress.active && (
                  <button
                    onClick={goBackToSelect}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '10px',
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                      marginBottom: '8px',
                    }}
                  >
                    ← Select Different Filament
                  </button>
                )}

                {/* Close Button - only show when not loading */}
                {!loadProgress.active && (
                  <button
                    onClick={closeModal}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '10px',
                      border: '1px solid #e5e7eb',
                      backgroundColor: '#f3f4f6',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    Done
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AmsStatusDisplay;
