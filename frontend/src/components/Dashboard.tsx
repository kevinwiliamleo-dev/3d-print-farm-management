import React, { useState, useEffect, useCallback } from 'react';
import { printFarmClient, PrinterResponse } from '../api/client';
import { PrinterCard } from './PrinterCard';
import { PrinterStatus } from './PrinterStatus';
import { QueueDashboard } from './QueueDashboard';
import { HistoryViewer } from './HistoryViewer';
import { JobUploadForm } from './JobUploadForm';
import { FilamentInventory } from './FilamentInventory';
import { useWebSocket } from '../hooks/useWebSocket';

type TabType = 'status' | 'queue' | 'history' | 'inventory' | 'settings';

interface DiscoveredPrinter {
  printer_id: string;
  printer_name: string;
  ip_address: string;
  model?: string;
}

export const Dashboard: React.FC = () => {
  const [printers, setPrinters] = useState<PrinterResponse[]>([]);
  const [selectedPrinterId, setSelectedPrinterId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [printerIp, setPrinterIp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [discoveredPrinters, setDiscoveredPrinters] = useState<DiscoveredPrinter[]>([]);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('status');
  const [queueRefreshKey, setQueueRefreshKey] = useState(0);
  const [cameraKey, setCameraKey] = useState(0);
  
  // Kit settings (persisted in localStorage)
  const [kits, setKits] = useState<Array<{id: string, ip: string, cameraConnected: boolean, fanConnected: boolean, fanState: 'ON' | 'OFF' | 'unknown'}>>(() => {
    const saved = localStorage.getItem('kits');
    return saved ? JSON.parse(saved) : [];
  });
  const [showAddKit, setShowAddKit] = useState(false);
  const [newKitIp, setNewKitIp] = useState('');
  const [newKitName, setNewKitName] = useState('');
  const [settingsSaved, setSettingsSaved] = useState(false);
  
  // Backwards compatibility
  const cameraKits = kits.map(k => ({ ...k, name: `Kit ${k.ip}`, connected: k.cameraConnected }));

  // Camera source selector: 'kit' or 'printer'
  const [selectedCameraSource, setSelectedCameraSource] = useState<string>(() => {
    return localStorage.getItem('selectedCameraSource') || 'kit';
  });

  // Compute actual camera source and URL based on selection
  const cameraSource: 'bambu' | 'custom' = selectedCameraSource === 'printer' ? 'bambu' : 'custom';
  const customCameraUrl = cameraKits.length > 0 ? `http://${cameraKits[0].ip}:8080/stream` : '';

  // Function to add new kit
  const handleAddKit = () => {
    if (!newKitIp) return;
    
    const newKit = {
      id: Date.now().toString(),
      ip: newKitIp,
      cameraConnected: false,
      fanConnected: false,
      fanState: 'unknown' as const,
    };
    
    const updatedKits = [...kits, newKit];
    setKits(updatedKits);
    localStorage.setItem('kits', JSON.stringify(updatedKits));
    localStorage.setItem('customCameraUrl', `http://${newKitIp}:8080/stream`);
    localStorage.setItem('cameraSource', 'custom');
    
    // Auto-configure bed cooling for first printer with this Kit IP
    configureKitForPrinter(newKitIp);
    
    setNewKitIp('');
    setNewKitName('');
    setShowAddKit(false);
    setSettingsSaved(true);
    setTimeout(() => setSettingsSaved(false), 3000);
    
    // Check status
    checkKitStatus(newKit.id, newKitIp);
  };

  // Auto-configure Kit IP for bed cooling
  const configureKitForPrinter = async (kitIp: string) => {
    try {
      // Get first printer ID (assuming single printer setup)
      const printer = printers[0];
      if (!printer) return;

      // Use dynamic backend URL (same hostname as frontend, port 5051)
      // so this works correctly from any device on the network
      const backendUrl = `${window.location.protocol}//${window.location.hostname}:5051`;
      await fetch(`${backendUrl}/api/printers/${printer.printerId}/bed-cooling/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kit_ip: kitIp, enabled: true })
      });
      
      console.log(`✅ Kit ${kitIp} configured for auto bed cooling on printer ${printer.printerId}`);
    } catch (err) {
      console.error('Failed to configure Kit for bed cooling:', err);
    }
  };

  // Function to remove kit
  const handleRemoveKit = (kitId: string) => {
    const updatedKits = kits.filter(k => k.id !== kitId);
    setKits(updatedKits);
    localStorage.setItem('kits', JSON.stringify(updatedKits));
  };

  // Check kit status (camera and fan)
  const checkKitStatus = async (kitId: string, ip: string) => {
    // Check camera - always try to get response even if HTTP error
    let cameraConnected = false;
    try {
      const cameraRes = await fetch(`http://${ip}:5000/kit/camera`, { signal: AbortSignal.timeout(3000) });
      const cameraData = await cameraRes.json();
      cameraConnected = cameraData.status === 'CAMERA RUNNING';
    } catch (err) {
      cameraConnected = false;
    }

    // Check fan
    let fanConnected = false;
    let fanState: 'ON' | 'OFF' | 'unknown' = 'unknown';
    try {
      const fanRes = await fetch(`http://${ip}:5000/kit/fan?state=status`, { signal: AbortSignal.timeout(3000) });
      const fanData = await fanRes.json();
      fanConnected = fanData.status === 'ON' || fanData.status === 'OFF';
      fanState = fanData.status === 'ON' ? 'ON' : 'OFF';
    } catch (err) {
      fanConnected = false;
      fanState = 'unknown';
    }

    // Update state once with all results
    setKits(prev => {
      const updated = prev.map(k => 
        k.id === kitId ? { ...k, cameraConnected, fanConnected, fanState } : k
      );
      localStorage.setItem('kits', JSON.stringify(updated));
      return updated;
    });
  };
  
  // For backwards compatibility
  const checkKitConnection = (kitId: string, ip: string) => checkKitStatus(kitId, ip);
  
  // Toggle fan - query actual ESP32 state first to avoid stale UI state
  const toggleFan = async (kitId: string, ip: string, currentState: string) => {
    try {
      // Always query actual ESP32 state first (UI state may be stale because polling is disabled)
      let actualState: 'ON' | 'OFF' | 'unknown' = 'unknown';
      try {
        const statusRes = await fetch(`http://${ip}:5000/kit/fan?state=status`, { signal: AbortSignal.timeout(3000) });
        const statusData = await statusRes.json();
        actualState = statusData.status === 'ON' ? 'ON' : 'OFF';
      } catch {
        // If status check fails, fall back to UI state
        actualState = (currentState === 'ON' || currentState === 'OFF') ? currentState as 'ON' | 'OFF' : 'OFF';
      }
      const newState = actualState === 'ON' ? 'off' : 'on';
      await fetch(`http://${ip}:5000/kit/fan?state=${newState}`);
      const newFanState = newState.toUpperCase() as 'ON' | 'OFF';
      setKits(prev => {
        const updated = prev.map(k =>
          k.id === kitId ? { ...k, fanState: newFanState, fanConnected: true } : k
        );
        localStorage.setItem('kits', JSON.stringify(updated));
        return updated;
      });
    } catch (err) {
      console.error('Failed to toggle fan:', err);
    }
  };

  // Refresh fan status for all kits (used when Settings tab opens)
  const refreshFanStatus = async () => {
    for (const kit of kits) {
      try {
        const res = await fetch(`http://${kit.ip}:5000/kit/fan?state=status`, { signal: AbortSignal.timeout(3000) });
        const data = await res.json();
        const fanState: 'ON' | 'OFF' = data.status === 'ON' ? 'ON' : 'OFF';
        setKits(prev => {
          const updated = prev.map(k =>
            k.id === kit.id ? { ...k, fanState, fanConnected: true } : k
          );
          localStorage.setItem('kits', JSON.stringify(updated));
          return updated;
        });
      } catch {
        // ignore, keep existing state
      }
    }
  };

  // Check all kits on mount and poll every 5 seconds
  useEffect(() => {
    // DISABLED: Kit feature not in use
    // Prevents 500 errors from legacy /kit/camera endpoint
    return; // Early return to skip kit polling
    
    // Initial check
    kits.forEach(kit => {
      checkKitStatus(kit.id, kit.ip);
    });
    
    // Poll kit status every 5 seconds to sync fan state
    const interval = setInterval(() => {
      kits.forEach(kit => {
        checkKitStatus(kit.id, kit.ip);
      });
    }, 5000);
    
    return () => clearInterval(interval);
  }, [kits.length]);

  // Auto-refresh fan status when Settings tab opens (fix stale UI state)
  useEffect(() => {
    if (activeTab === 'settings' && kits.length > 0) {
      refreshFanStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const refreshQueue = useCallback(() => {
    setQueueRefreshKey(k => k + 1);
  }, []);

  // WebSocket for real-time updates
  const { isConnected: wsConnected, printers: wsPrinters } = useWebSocket({
    onStatusUpdate: (statusPrinters) => {
      // Update printer statuses from WebSocket
      setPrinters(prev => prev.map(p => {
        const wsP = statusPrinters.find(ws => ws.printerId === p.printerId);
        if (wsP) {
          return {
            ...p,
            status: wsP.status,
            mqttConnected: wsP.mqttConnected,
          };
        }
        return p;
      }));
    }
  });

  const loadPrinters = useCallback(async () => {
    try {
      const list = await printFarmClient.getAllPrinters();
      
      // Merge new data with existing printer state to preserve MQTT data
      setPrinters(prev => {
        if (prev.length === 0) {
          // First load - use data as-is
          return list;
        }
        
        // Merge: keep MQTT data (progress, temp, etc.) but update basic fields
        return list.map(newPrinter => {
          const existing = prev.find(p => p.printerId === newPrinter.printerId);
          if (existing) {
            // Merge: preserve runtime data, update static fields AND temperature
            return {
              ...existing, // Keep MQTT data (progress, layers, etc.)
              printerName: newPrinter.printerName,
              status: newPrinter.status,
              mqttConnected: newPrinter.mqttConnected,
              autoContinue: newPrinter.autoContinue, // Update toggle state
              // Update temperature data from API
              nozzleTemp: newPrinter.nozzleTemp,
              nozzleTargetTemp: newPrinter.nozzleTargetTemp,
              bedTemp: newPrinter.bedTemp,
              bedTargetTemp: newPrinter.bedTargetTemp,
              chamberTemp: newPrinter.chamberTemp,
              remainingTime: newPrinter.remainingTime,
              currentFile: newPrinter.currentFile,
              printError: newPrinter.printError,
            };
          }
          return newPrinter; // New printer
        });
      });
      
      if (list.length > 0 && !selectedPrinterId) {
        setSelectedPrinterId(list[0].printerId);
      }

      // Sync kit IP from database so ALL devices (mobile, tablet, etc.) auto-load
      // the kit config without needing to re-enter it
      const dbKitIp = (list[0] as any)?.kitIp;
      if (dbKitIp) {
        setKits(prev => {
          const alreadyExists = prev.some(k => k.ip === dbKitIp);
          if (!alreadyExists) {
            const synced = [{
              id: 'db-synced',
              ip: dbKitIp,
              cameraConnected: false,
              fanConnected: false,
              fanState: 'unknown' as const
            }];
            localStorage.setItem('kits', JSON.stringify(synced));
            return synced;
          }
          return prev;
        });
      }
    } catch (err) {
      console.error('Failed to load printers:', err);
    }
  }, [selectedPrinterId]);

  // Fetch MQTT status including temperature for selected printer
  const loadMqttStatus = useCallback(async () => {
    if (!selectedPrinterId) return;
    
    try {
      const mqttStatus = await printFarmClient.getMqttStatus(selectedPrinterId);
      
      // Update printer with MQTT data (temperature, progress, layer, etc.)
      setPrinters(prev => prev.map(p => {
        if (p.printerId === selectedPrinterId) {
          return {
            ...p,
            status: mqttStatus.printer_status || p.status,
            mqttConnected: mqttStatus.mqtt_connected,
            progress: mqttStatus.print_progress || 0,
            remainingTime: mqttStatus.remaining_time || 0,
            currentFile: mqttStatus.current_file || '',
            currentLayer: mqttStatus.current_layer || 0,
            totalLayers: mqttStatus.total_layers || 0,
            nozzleTemp: mqttStatus.nozzle_temp || 0,
            nozzleTargetTemp: mqttStatus.nozzle_target_temp || 0,
            bedTemp: mqttStatus.bed_temp || 0,
            bedTargetTemp: mqttStatus.bed_target_temp || 0,
            chamberTemp: mqttStatus.chamber_temp || 0,
            printError: mqttStatus.print_error || 0,
            printStage: mqttStatus.print_stage || 0,
          };
        }
        return p;
      }));
    } catch (err) {
      console.error('Failed to load MQTT status:', err);
    }
  }, [selectedPrinterId]);

  useEffect(() => {
    loadPrinters();
    const interval = setInterval(loadPrinters, 30000);
    return () => clearInterval(interval);
  }, [loadPrinters]);

  // Poll MQTT status every 5 seconds for temperature updates
  // (FDM Monster uses 5-15 second intervals to reduce load)
  useEffect(() => {
    loadMqttStatus();
    const interval = setInterval(loadMqttStatus, 5000);
    return () => clearInterval(interval);
  }, [loadMqttStatus]);

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  // Auto scan when modal opens
  const handleScanNetwork = async () => {
    setIsScanning(true);
    setDiscoveredPrinters([]);
    try {
      const found = await printFarmClient.discoverPrintersOnNetwork();
      // Transform to DiscoveredPrinter format
      const discovered = found.map((p: any) => ({
        printer_id: p.printerId || p.printer_id,
        printer_name: p.printerName || p.printer_name || 'Unknown Printer',
        ip_address: p.ipAddress || p.ip_address || p.printerIp || '',
        model: p.model || 'Bambu Lab',
      }));
      setDiscoveredPrinters(discovered);
      if (discovered.length === 0) {
        setMessage({ type: 'error', text: 'No printers found on network. Try entering IP manually.' });
      }
    } catch (err: any) {
      console.error('Scan failed:', err);
      setMessage({ type: 'error', text: 'Network scan failed. Try entering IP manually.' });
    } finally {
      setIsScanning(false);
    }
  };

  const handleAddDiscoveredPrinter = async (printer: DiscoveredPrinter) => {
    // Prompt for access code
    const accessCode = window.prompt(
      `Enter Access Code for ${printer.printer_name}:\n\n` +
      `You can find it in Bambu Studio:\n` +
      `Settings → Network → Access Code`,
      ''
    );
    
    if (!accessCode || accessCode.trim() === '') {
      setMessage({ type: 'error', text: 'Access code is required' });
      return;
    }
    
    setIsLoading(true);
    try {
      // Use new discovery endpoint with full credentials
      const response = await fetch(`${window.location.protocol}//${window.location.hostname}:5051/api/discovery/add-discovered`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip: printer.ip_address,
          name: printer.printer_name,
          serial: printer.printer_id,
          model: printer.model || 'Bambu Lab',
          access_code: accessCode.trim()
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        await loadPrinters();
        setShowAddModal(false);
        setDiscoveredPrinters([]);
        setMessage({ type: 'success', text: `Printer added: ${printer.printer_name}` });
      } else {
        setMessage({ type: 'error', text: result.message || 'Failed to add printer' });
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || 'Failed to add printer' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddPrinter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!printerIp.trim()) return;

    setIsLoading(true);
    try {
      const result = await printFarmClient.discoverByIp(printerIp);
      if (result.found) {
        try {
          await printFarmClient.registerPrinter(result.printer.printer_id, result.printer.printer_name);
        } catch (e: any) {
          if (e.response?.status !== 400) throw e;
        }
        await loadPrinters();
        setPrinterIp('');
        setShowAddModal(false);
        setMessage({ type: 'success', text: `Printer added: ${result.printer.printer_name}` });
      } else {
        setMessage({ type: 'error', text: 'No printer found at this IP' });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to add printer' });
    } finally {
      setIsLoading(false);
    }
  };

  const selectedPrinter = printers.find(p => p.printerId === selectedPrinterId) || null;

  // Count stats
  const printingCount = printers.filter(p => p.status === 'printing').length;
  const idleCount = printers.filter(p => p.status === 'idle').length;
  const offlineCount = printers.filter(p => !p.status || p.status === 'offline').length;

  return (
    <div className="dashboard-container" style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f9fafb',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      {/* Header with Stats */}
      <header className="dashboard-header" style={{
        backgroundColor: '#ffffff',
        borderBottom: '1px solid #e5e7eb',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '28px' }}>🏭</span>
          <div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: '#1f2937' }}>
              Print Farm Manager
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <p style={{ margin: 0, fontSize: '13px', color: '#6b7280' }}>
                Monitor and control your 3D printers
              </p>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                padding: '2px 6px',
                borderRadius: '9999px',
                backgroundColor: wsConnected ? '#dcfce7' : '#fee2e2',
                color: wsConnected ? '#166534' : '#991b1b',
              }}>
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: wsConnected ? '#22c55e' : '#ef4444',
                }}></span>
                {wsConnected ? 'Live' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>

        {/* Stats in Header */}
        <div className="header-stats-row" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
            <span style={{ fontSize: '16px' }}>🖨️</span>
            <span style={{ fontSize: '18px', fontWeight: 700, color: '#1f2937' }}>{printers.length}</span>
            <span style={{ fontSize: '11px', color: '#6b7280' }}>Total</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', backgroundColor: '#fffbeb', borderRadius: '8px' }}>
            <span style={{ fontSize: '16px' }}>🔥</span>
            <span style={{ fontSize: '18px', fontWeight: 700, color: '#b45309' }}>{printingCount}</span>
            <span style={{ fontSize: '11px', color: '#92400e' }}>Printing</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', backgroundColor: '#ecfdf5', borderRadius: '8px' }}>
            <span style={{ fontSize: '16px' }}>✅</span>
            <span style={{ fontSize: '18px', fontWeight: 700, color: '#047857' }}>{idleCount}</span>
            <span style={{ fontSize: '11px', color: '#065f46' }}>Ready</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', backgroundColor: '#f3f4f6', borderRadius: '8px' }}>
            <span style={{ fontSize: '16px' }}>⚫</span>
            <span style={{ fontSize: '18px', fontWeight: 700, color: '#6b7280' }}>{offlineCount}</span>
            <span style={{ fontSize: '11px', color: '#6b7280' }}>Offline</span>
          </div>
        </div>

        <button
          className="header-find-btn"
          onClick={() => setShowAddModal(true)}
          style={{
            padding: '12px 24px',
            borderRadius: '8px',
            border: 'none',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            fontSize: '15px',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
          }}
        >
          🔍 Find Printer
        </button>
      </header>

      {/* Notification Toast */}
      {message && (
        <div style={{
          position: 'fixed',
          top: '80px',
          right: '24px',
          padding: '12px 20px',
          borderRadius: '8px',
          backgroundColor: message.type === 'success' ? '#d1fae5' : '#fee2e2',
          color: message.type === 'success' ? '#065f46' : '#991b1b',
          fontSize: '14px',
          fontWeight: 500,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          zIndex: 1000,
        }}>
          {message.type === 'success' ? '✓' : '✕'} {message.text}
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        {/* Collapsible Sidebar */}
        <div className="sidebar-container">
          {/* Tab indicator (visible when collapsed) */}
          <div className="sidebar-tab">
            <span className="sidebar-tab-icon">🖨️</span>
            <span className="sidebar-tab-count">{printers.length}</span>
          </div>
          
          {/* Sidebar panel (visible on hover) */}
          <div className="sidebar-panel">
            <div className="printer-list-section">
              <h2 style={{ 
                margin: '0 0 16px', 
                fontSize: '16px', 
                fontWeight: 600, 
                color: '#1f2937' 
              }}>
                Printers ({printers.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {printers.length === 0 ? (
                  <div style={{
                    padding: '40px',
                    textAlign: 'center',
                    backgroundColor: '#ffffff',
                    borderRadius: '12px',
                    border: '2px dashed #e5e7eb',
                  }}>
                    <div style={{ fontSize: '40px', marginBottom: '12px' }}>🖨️</div>
                    <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
                      No printers added yet
                    </div>
                    <button
                      onClick={() => setShowAddModal(true)}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: '#3b82f6',
                        color: '#ffffff',
                        fontSize: '13px',
                        cursor: 'pointer',
                      }}
                    >
                      Add Your First Printer
                    </button>
                  </div>
                ) : (
                  printers.map((printer) => (
                    <PrinterCard
                      key={printer.printerId}
                      printer={printer}
                      isSelected={selectedPrinterId === printer.printerId}
                      onSelect={() => setSelectedPrinterId(printer.printerId)}
                      onRefresh={loadPrinters}
                      onDelete={loadPrinters}
                      onJobAdded={refreshQueue}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel with Tabs */}
        <div style={{ minWidth: 0 }}>
          {/* Tab Navigation with Status indicators */}
          <div className="tab-navigation" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="tab-bar-tabs" style={{ display: 'flex', gap: '8px' }}>
              {[
                { id: 'status' as TabType, label: '📊 Status', icon: '📊' },
                { id: 'queue' as TabType, label: '📋 Queue & Upload', icon: '📋' },
                { id: 'inventory' as TabType, label: '🧵 Inventory', icon: '🧵' },
                { id: 'history' as TabType, label: '📜 History', icon: '📜' },
                { id: 'settings' as TabType, label: '⚙️ Settings', icon: '⚙️' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    if (tab.id === 'status') setCameraKey(prev => prev + 1);
                  }}
                  className="tab-button"
                  style={{
                    backgroundColor: activeTab === tab.id ? '#3b82f6' : 'transparent',
                    color: activeTab === tab.id ? '#ffffff' : '#6b7280',
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            
            {/* Printer name + Status & MQTT indicators */}
            {selectedPrinter && (
              <div className="tab-status-row" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                {/* Printer name */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#1f2937',
                }}>
                  <span>🖨️</span>
                  <span>{selectedPrinter.printerName || 'Unknown Printer'}</span>
                </div>
                
                <div style={{ width: '1px', height: '20px', backgroundColor: '#e5e7eb' }} />
                
                <div style={{
                  backgroundColor: selectedPrinter.status === 'printing' ? '#fffbeb' : selectedPrinter.status === 'idle' ? '#ecfdf5' : '#f9fafb',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                }}>
                  <span style={{ color: '#6b7280' }}>Status:</span>
                  <span style={{ 
                    fontWeight: 600, 
                    color: selectedPrinter.status === 'printing' ? '#f59e0b' : selectedPrinter.status === 'idle' ? '#059669' : '#6b7280',
                  }}>
                    {selectedPrinter.status === 'printing' 
                      ? `Printing ${selectedPrinter.progress || 0}%` 
                      : selectedPrinter.status === 'idle' 
                        ? 'Idle' 
                        : (selectedPrinter.status ? selectedPrinter.status.charAt(0).toUpperCase() + selectedPrinter.status.slice(1) : 'Unknown')}
                  </span>
                </div>
                <div style={{
                  backgroundColor: selectedPrinter.mqttConnected ? '#ecfdf5' : '#fef2f2',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                }}>
                  <span style={{ 
                    width: '6px', 
                    height: '6px', 
                    borderRadius: '50%', 
                    backgroundColor: selectedPrinter.mqttConnected ? '#22c55e' : '#ef4444' 
                  }} />
                  <span style={{ color: '#6b7280' }}>MQTT:</span>
                  <span style={{ 
                    fontWeight: 600, 
                    color: selectedPrinter.mqttConnected ? '#059669' : '#dc2626' 
                  }}>
                    {selectedPrinter.mqttConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Tab Content */}
          {activeTab === 'status' && (
            <PrinterStatus 
              key={cameraKey}
              printer={selectedPrinter} 
              cameraSource={cameraSource}
              customCameraUrl={customCameraUrl}
            />
          )}
          
          {activeTab === 'queue' && selectedPrinterId && (
            <QueueDashboard 
              key={queueRefreshKey}
              printerId={selectedPrinterId} 
              onRefresh={loadPrinters}
              showUpload={true}
              printers={printers.map(p => ({ printerId: p.printerId, printerName: p.printerName }))}
            />
          )}
          
          {activeTab === 'inventory' && (
            <FilamentInventory />
          )}
          
          {activeTab === 'history' && (
            <HistoryViewer printerId={selectedPrinterId || undefined} />
          )}
          
          {activeTab === 'settings' && (
            <div style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '24px',
            }}>
              <h2 style={{ margin: '0 0 24px 0', fontSize: '18px', fontWeight: 600, color: '#1f2937' }}>
                ⚙️ Settings
              </h2>
              
              {/* Kit Section */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  marginBottom: '16px',
                }}>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#374151' }}>
                    🔧 Kit
                  </h3>
                  {!showAddKit && (
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button
                        onClick={() => setShowAddKit(true)}
                        style={{
                          padding: '10px 20px',
                          borderRadius: '8px',
                          border: 'none',
                          backgroundColor: '#3b82f6',
                          color: '#ffffff',
                          fontSize: '14px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                        }}
                      >
                        ➕ Add Kit
                      </button>
                      <button
                        onClick={() => window.open('https://tokopedia.link/your-kit-link', '_blank')}
                        style={{
                          padding: '10px 20px',
                          borderRadius: '8px',
                          border: '1px solid #f97316',
                          backgroundColor: '#fff7ed',
                          color: '#ea580c',
                          fontSize: '14px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                        }}
                      >
                        🛒 Purchase Kit
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Add Kit Form */}
                {showAddKit && (
                  <div style={{
                    padding: '20px',
                    backgroundColor: '#f0f9ff',
                    borderRadius: '12px',
                    border: '2px solid #3b82f6',
                    marginBottom: '16px',
                  }}>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                      <input
                        type="text"
                        value={newKitIp}
                        onChange={(e) => setNewKitIp(e.target.value)}
                        placeholder="0.0.0.0"
                        style={{
                          flex: 1,
                          padding: '12px 16px',
                          borderRadius: '8px',
                          border: '1px solid #d1d5db',
                          fontSize: '14px',
                          boxSizing: 'border-box',
                        }}
                      />
                      <button
                        onClick={() => { setShowAddKit(false); setNewKitIp(''); setNewKitName(''); }}
                        style={{
                          padding: '12px 20px',
                          borderRadius: '8px',
                          border: '1px solid #d1d5db',
                          backgroundColor: '#ffffff',
                          color: '#374151',
                          fontSize: '14px',
                          cursor: 'pointer',
                        }}
                      >
                        Batal
                      </button>
                      <button
                        onClick={handleAddKit}
                        disabled={!newKitIp}
                        style={{
                          padding: '12px 24px',
                          borderRadius: '8px',
                          border: 'none',
                          backgroundColor: newKitIp ? '#22c55e' : '#9ca3af',
                          color: '#ffffff',
                          fontSize: '14px',
                          fontWeight: 600,
                          cursor: newKitIp ? 'pointer' : 'not-allowed',
                        }}
                      >
                        💾 Save
                      </button>
                    </div>
                  </div>
                )}
                
                {/* List of Kits */}
                {kits.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {kits.map((kit) => (
                      <div
                        key={kit.id}
                        style={{
                          padding: '16px',
                          backgroundColor: '#f9fafb',
                          borderRadius: '12px',
                          border: '1px solid #e5e7eb',
                        }}
                      >
                        {/* IP and Actions */}
                        <div style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          alignItems: 'center',
                          marginBottom: '12px',
                        }}>
                          <div style={{ 
                            fontSize: '16px', 
                            fontWeight: 600, 
                            color: '#1f2937',
                            fontFamily: 'monospace',
                          }}>
                            {kit.ip}
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                              onClick={() => checkKitStatus(kit.id, kit.ip)}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                backgroundColor: '#ffffff',
                                color: '#374151',
                                fontSize: '12px',
                                cursor: 'pointer',
                              }}
                            >
                              🔄 Refresh
                            </button>
                            <button
                              onClick={() => handleRemoveKit(kit.id)}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: '1px solid #fecaca',
                                backgroundColor: '#fef2f2',
                                color: '#dc2626',
                                fontSize: '12px',
                                cursor: 'pointer',
                              }}
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                        
                        {/* Status Row */}
                        <div style={{ display: 'flex', gap: '16px' }}>
                          {/* Camera Status */}
                          <div style={{ 
                            flex: 1,
                            padding: '12px',
                            backgroundColor: '#ffffff',
                            borderRadius: '8px',
                            border: '1px solid #e5e7eb',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '20px' }}>📷</span>
                                <div style={{ fontSize: '13px', fontWeight: 500, color: '#374151' }}>Camera</div>
                              </div>
                              <div style={{ 
                                padding: '4px 10px',
                                borderRadius: '12px',
                                backgroundColor: kit.cameraConnected ? '#dcfce7' : '#fee2e2',
                                color: kit.cameraConnected ? '#166534' : '#991b1b',
                                fontSize: '11px',
                                fontWeight: 600,
                              }}>
                                {kit.cameraConnected ? '🟢 Online' : '🔴 Offline'}
                              </div>
                            </div>
                            {/* Camera Source Dropdown */}
                            <select
                              value={selectedCameraSource}
                              onChange={(e) => {
                                setSelectedCameraSource(e.target.value);
                                localStorage.setItem('selectedCameraSource', e.target.value);
                              }}
                              style={{
                                width: '100%',
                                padding: '8px 10px',
                                borderRadius: '6px',
                                border: '1px solid #d1d5db',
                                fontSize: '12px',
                                backgroundColor: '#f9fafb',
                                cursor: 'pointer',
                              }}
                            >
                              <option value="kit">📹 Camera Kit</option>
                              <option value="printer">🖨️ Camera Printer</option>
                            </select>
                            {/* Save Button */}
                            <button
                              onClick={() => {
                                localStorage.setItem('selectedCameraSource', selectedCameraSource);
                                setSettingsSaved(true);
                                setTimeout(() => setSettingsSaved(false), 2000);
                              }}
                              style={{
                                marginTop: '8px',
                                width: '100%',
                                padding: '8px 16px',
                                borderRadius: '6px',
                                border: 'none',
                                backgroundColor: '#22c55e',
                                color: '#ffffff',
                                fontSize: '12px',
                                fontWeight: 600,
                                cursor: 'pointer',
                              }}
                            >
                              💾 Save
                            </button>
                          </div>
                          
                          {/* Fan Toggle */}
                          <div style={{ 
                            flex: 1,
                            padding: '12px',
                            backgroundColor: '#ffffff',
                            borderRadius: '8px',
                            border: '1px solid #e5e7eb',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span style={{ fontSize: '20px' }}>🌀</span>
                              <div style={{ fontSize: '13px', fontWeight: 500, color: '#374151' }}>Fan</div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{ 
                                padding: '4px 10px',
                                borderRadius: '12px',
                                backgroundColor: kit.fanConnected ? '#dcfce7' : '#fee2e2',
                                color: kit.fanConnected ? '#166534' : '#991b1b',
                                fontSize: '11px',
                                fontWeight: 600,
                              }}>
                                {kit.fanConnected ? '🟢 Connected' : '🔴 Offline'}
                              </div>
                              <button
                                onClick={() => toggleFan(kit.id, kit.ip, kit.fanState)}
                                style={{
                                  padding: '6px 14px',
                                  borderRadius: '20px',
                                  border: 'none',
                                  backgroundColor: kit.fanState === 'ON' ? '#22c55e' : '#6b7280',
                                  color: '#ffffff',
                                  fontSize: '11px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                }}
                              >
                                {kit.fanState === 'ON' ? 'ON' : 'OFF'}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                
                {settingsSaved && (
                  <div style={{ 
                    marginTop: '16px',
                    padding: '12px 16px',
                    backgroundColor: '#dcfce7',
                    borderRadius: '8px',
                    color: '#166534',
                    fontSize: '14px',
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}>
                    ✓ Kit berhasil ditambahkan!
                  </div>
                )}
              </div>
              
              {/* System Info */}
              <div>
                <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 600, color: '#374151' }}>
                  ℹ️ System Info
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '12px 16px',
                    backgroundColor: '#f9fafb',
                    borderRadius: '8px',
                  }}>
                    <div style={{ fontSize: '13px', color: '#374151' }}>API Server</div>
                    <div style={{ 
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}>
                      <span style={{ fontSize: '12px', color: '#6b7280' }}>http://localhost:5000</span>
                      <div style={{ 
                        padding: '3px 8px', 
                        borderRadius: '4px', 
                        backgroundColor: wsConnected ? '#dcfce7' : '#fee2e2',
                        color: wsConnected ? '#166534' : '#991b1b',
                        fontSize: '11px',
                        fontWeight: 500,
                      }}>
                        {wsConnected ? '🟢 Connected' : '🔴 Offline'}
                      </div>
                    </div>
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '12px 16px',
                    backgroundColor: '#f9fafb',
                    borderRadius: '8px',
                  }}>
                    <div style={{ fontSize: '13px', color: '#374151' }}>Printers</div>
                    <span style={{ fontSize: '12px', color: '#6b7280' }}>{printers.length} registered</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Printer Modal */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              marginBottom: '24px',
            }}>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
                🔍 Find Printer
              </h2>
              <button
                onClick={() => { setShowAddModal(false); setDiscoveredPrinters([]); }}
                style={{
                  border: 'none',
                  background: 'none',
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: '#9ca3af',
                }}
              >
                ✕
              </button>
            </div>

            {/* Auto Scan Section */}
            <div style={{
              backgroundColor: '#f0f9ff',
              border: '1px solid #bae6fd',
              borderRadius: '12px',
              padding: '20px',
              marginBottom: '20px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#0369a1' }}>
                    🌐 Auto Scan Network
                  </h3>
                  <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#0284c7' }}>
                    Automatically find Bambu Lab printers on your network
                  </p>
                </div>
                <button
                  onClick={handleScanNetwork}
                  disabled={isScanning}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: isScanning ? '#94a3b8' : '#0ea5e9',
                    color: '#ffffff',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: isScanning ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  {isScanning ? (
                    <>
                      <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                      Scanning...
                    </>
                  ) : (
                    <>📡 Scan Now</>
                  )}
                </button>
              </div>

              {/* Discovered Printers List */}
              {discoveredPrinters.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <div style={{ fontSize: '13px', fontWeight: 500, color: '#0369a1', marginBottom: '8px' }}>
                    Found {discoveredPrinters.length} printer(s):
                  </div>
                  {discoveredPrinters.map((printer) => (
                    <div
                      key={printer.printer_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '12px 16px',
                        backgroundColor: '#ffffff',
                        borderRadius: '8px',
                        marginBottom: '8px',
                        border: '1px solid #e0f2fe',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1e293b' }}>
                          🖨️ {printer.printer_name}
                        </div>
                        <div style={{ fontSize: '12px', color: '#64748b' }}>
                          {printer.ip_address} • {printer.model}
                        </div>
                      </div>
                      <button
                        onClick={() => handleAddDiscoveredPrinter(printer)}
                        disabled={isLoading}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '6px',
                          border: 'none',
                          backgroundColor: '#22c55e',
                          color: '#ffffff',
                          fontSize: '13px',
                          fontWeight: 500,
                          cursor: isLoading ? 'not-allowed' : 'pointer',
                        }}
                      >
                        ✓ Add
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {isScanning && (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '20px',
                  color: '#0284c7',
                  fontSize: '14px',
                }}>
                  🔍 Scanning network for printers...
                </div>
              )}
            </div>

            {/* Divider */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              marginBottom: '20px',
            }}>
              <div style={{ flex: 1, height: '1px', backgroundColor: '#e5e7eb' }}></div>
              <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 500 }}>OR</span>
              <div style={{ flex: 1, height: '1px', backgroundColor: '#e5e7eb' }}></div>
            </div>

            {/* Manual IP Section */}
            <form onSubmit={handleAddPrinter}>
              <label style={{ 
                display: 'block', 
                fontSize: '14px', 
                fontWeight: 500, 
                color: '#374151',
                marginBottom: '8px',
              }}>
                📝 Enter IP Manually
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={printerIp}
                  onChange={(e) => setPrinterIp(e.target.value)}
                  placeholder="192.168.1.100"
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    borderRadius: '8px',
                    border: '1px solid #d1d5db',
                    fontSize: '14px',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="submit"
                  disabled={isLoading || !printerIp.trim()}
                  style={{
                    padding: '12px 20px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: isLoading || !printerIp.trim() ? '#9ca3af' : '#3b82f6',
                    color: '#ffffff',
                    fontSize: '14px',
                    fontWeight: 500,
                    cursor: isLoading || !printerIp.trim() ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isLoading ? '...' : 'Add'}
                </button>
              </div>
              <p style={{ 
                fontSize: '12px', 
                color: '#6b7280', 
                marginTop: '8px',
                marginBottom: '0',
              }}>
                Make sure your Bambu Lab printer is in LAN mode
              </p>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
