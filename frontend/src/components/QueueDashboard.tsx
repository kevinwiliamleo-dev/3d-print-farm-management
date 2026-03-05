import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { printFarmClient, JobMetadata, PrintPreviewResponse, PrintPreviewStep, PrintPreset } from '../api/client';
import { PrinterFilesTab } from './PrinterFilesTab';
import { useWebSocket } from '../hooks/useWebSocket';

interface PrinterInfo {
  printerId: string;
  printerName: string;
}

interface AmsTray {
  slot: number;
  color: string;      // Hex color like "#FFFFFF"
  type: string;       // e.g., "PLA Basic", "PETG"
  name: string;       // Full name like "Bambu PLA Basic"
  remain: number;     // Percentage remaining (0-100)
  empty: boolean;     // True if slot is empty
  is_external?: boolean;
  // Extended info from slot assignments
  brand?: string;
  nozzle_temp_default?: number;
  bed_temp_default?: number;
  remaining_grams?: number;
  spool_weight?: number;
  filament_id?: number;  // Filament profile ID for temperature overrides
}

interface QueueItem {
  queue_id: number;
  job_id: number;
  job_name: string;
  position_in_queue: number;
  current_loop: number;
  loop_count: number;
  status: string;
}

interface QueueStats {
  printer_id: string;
  total_items: number;
  pending_items: number;
  running_items: number;
  completed_items: number;
}

interface PrinterUploadProgress {
  percent: number;
  bytes_sent: number;
  total_bytes: number;
  filename: string;
  status: string;
}

interface QueueDashboardProps {
  printerId: string;
  onRefresh?: () => void;
  showUpload?: boolean;
  printers?: PrinterInfo[];
  printerStatus?: string; // 'printing' | 'idle' | 'paused' | 'offline'
}

export const QueueDashboard: React.FC<QueueDashboardProps> = ({ printerId, onRefresh, showUpload = false, printers = [], printerStatus }) => {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedUploadPrinter, setSelectedUploadPrinter] = useState<string>(printerId || '');
  const [loopCount, setLoopCount] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Preview state (after upload, before queue)
  const [uploadedJobId, setUploadedJobId] = useState<number | null>(null);
  const [uploadedJobName, setUploadedJobName] = useState<string>('');
  const [jobMetadata, setJobMetadata] = useState<JobMetadata | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  
  // Print steps preview
  const [printPreview, setPrintPreview] = useState<PrintPreviewResponse | null>(null);
  const [showSteps, setShowSteps] = useState(false);
  
  // Preview modal tab state
  const [previewTab, setPreviewTab] = useState<'job' | 'gcode'>('job');
  
  // GCode Section interfaces (matches backend structure)
  interface GCodeSubSection {
    id: string;
    name: string;
    icon: string;
    startLine: number;
    endLine: number;
    enabled: boolean;
    canDisable: boolean;
    lines: string[];
  }
  
  interface GCodeSection {
    id: number;
    title: string;
    icon: string;
    phase: 'preparation' | 'printing' | 'completion';
    startLine: number;
    endLine: number;
    subSections: GCodeSubSection[];
    enabled: boolean;
    canDisable: boolean;
    layerCount?: number;
    lineCount?: number;
  }
  
  // GCode viewer state
  const [gcodeData, setGcodeData] = useState<{
    job_id: number;
    job_name: string;
    gcode: string[];
    total_lines: number;
    plates: string[];
    selected_plate: string;
    sections?: GCodeSection[];
    printBodyStart?: number;
    endGcodeStart?: number;
  } | null>(null);
  const [gcodeLoading, setGcodeLoading] = useState(false);
  const [gcodeError, setGcodeError] = useState<string | null>(null);
  const [gcodeSearch, setGcodeSearch] = useState('');
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [highlightSyntax, setHighlightSyntax] = useState(true);
  const [expandedGcodeStep, setExpandedGcodeStep] = useState<number | null>(null);
  const [gcodeViewMode, setGcodeViewMode] = useState<'steps' | 'raw'>('steps');
  
  // AMS filament state
  const [amsTrays, setAmsTrays] = useState<AmsTray[]>([]);
  const [selectedAmsSlot, setSelectedAmsSlot] = useState<number>(0);
  const [useAms, setUseAms] = useState<boolean>(true);
  const [currentlyLoadedSlot, setCurrentlyLoadedSlot] = useState<number>(255); // tray_now from printer (255 = none)
  
  // Temperature display (from selected filament, for preview - not saved until queue add)
  const [displayNozzleTemp, setDisplayNozzleTemp] = useState<number | null>(null);
  const [displayBedTemp, setDisplayBedTemp] = useState<number | null>(null);
  const [originalNozzleTemp, setOriginalNozzleTemp] = useState<number | null>(null);
  const [originalBedTemp, setOriginalBedTemp] = useState<number | null>(null);
  
  // ==================== AUTOMATION SETTINGS (Per Job) ====================
  const [autoBedLeveling, setAutoBedLeveling] = useState<boolean>(true);
  const [flowCalibration, setFlowCalibration] = useState<boolean>(false);
  const [timelapse, setTimelapse] = useState<boolean>(false);
  
  // Generate dynamic steps based on user's automation settings
  // Based on actual Bambu A1 gcode sequence
  // DISABLED: Direct print mode - no automation settings to display
  const dynamicSteps = useMemo((): PrintPreviewStep[] => {
    return []; // Skip preview in direct print mode
  }, [printPreview]);

  // Printer upload progress (for Start Next Job)
  
  // Printer upload progress (for Start Next Job)
  const [printerUploadProgress, setPrinterUploadProgress] = useState<PrinterUploadProgress | null>(null);
  const [isStartingJob, setIsStartingJob] = useState(false);
  
  // Edit queue item state
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingQueueId, setEditingQueueId] = useState<number | null>(null);
  const [editingQueueDetails, setEditingQueueDetails] = useState<any>(null);
  const [isLoadingEditDetails, setIsLoadingEditDetails] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  
  // Edit modal form state (simplified - 3 checkboxes + AMS only)
  const [editAmsSlot, setEditAmsSlot] = useState<number>(0);
  const [editUseAms, setEditUseAms] = useState<boolean>(true);
  const [editFilamentAlreadyLoaded, setEditFilamentAlreadyLoaded] = useState<boolean>(false);
  const [editAutoBedLeveling, setEditAutoBedLeveling] = useState<boolean>(true);
  const [editFlowCalibration, setEditFlowCalibration] = useState<boolean>(false);
  const [editTimelapse, setEditTimelapse] = useState<boolean>(false);
  
  // Bucket List state
  const [bucketItems, setBucketItems] = useState<any[]>([]);
  const [isLoadingBucket, setIsLoadingBucket] = useState(false);
  const [showBucketSection, setShowBucketSection] = useState(true);
  
  // WebSocket for real-time upload progress
  useWebSocket({
    onUploadProgress: (incomingPrinterId, progress) => {
      console.log('Upload progress received:', incomingPrinterId, progress);
      if (incomingPrinterId === printerId) {
        setPrinterUploadProgress(progress);
        
        // Clear progress after completion or failure
        if (progress.status === 'print_started' || progress.status === 'print_failed' || progress.status === 'failed') {
          setTimeout(() => {
            setPrinterUploadProgress(null);
            setIsStartingJob(false);
            loadQueue();
          }, 2000);
        }
      }
    }
  });

  const loadQueue = useCallback(async () => {
    if (!printerId) return;
    
    setIsLoading(true);
    try {
      const [queueData, statsData] = await Promise.all([
        printFarmClient.getQueueForPrinter(printerId),
        printFarmClient.getQueueStatus(printerId)
      ]);
      
      // Transform to consistent format
      const items = (queueData || []).map((item: any) => ({
        queue_id: item.queue_id || item.queueId,
        job_id: item.job_id || item.jobId,
        job_name: item.job_name || item.jobName || `Job #${item.job_id || item.jobId}`,
        position_in_queue: item.position_in_queue || item.positionInQueue,
        current_loop: item.current_loop || item.currentLoop || 0,
        loop_count: item.loop_count || item.loopCount || 1,
        status: item.status || item.queueStatus || 'pending'
      }));
      
      setQueueItems(items);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load queue:', err);
    } finally {
      setIsLoading(false);
    }
  }, [printerId]);

  // GCode line type classification for syntax highlighting
  const getGCodeLineType = (line: string): 'comment' | 'move' | 'temp' | 'setting' | 'layer' | 'retract' | 'special' | 'default' => {
    const trimmed = line.trim();
    if (trimmed.startsWith(';')) return 'comment';
    if (trimmed.startsWith('G0 ') || trimmed.startsWith('G1 ')) return 'move';
    if (trimmed.match(/^M10[49]/)) return 'temp';
    if (trimmed.match(/^M14[01]/)) return 'temp';
    if (trimmed.match(/^M190/)) return 'temp';
    if (trimmed.match(/^;LAYER:/i)) return 'layer';
    if (trimmed.match(/^G10|^G11/)) return 'retract';
    if (trimmed.match(/^M[0-9]+/)) return 'setting';
    if (trimmed.match(/^G[0-9]+/)) return 'special';
    return 'default';
  };

  const getGCodeLineColor = (type: string): string => {
    switch (type) {
      case 'comment': return '#9ca3af';
      case 'move': return '#3b82f6';
      case 'temp': return '#f97316';
      case 'setting': return '#a855f7';
      case 'layer': return '#22c55e';
      case 'retract': return '#eab308';
      case 'special': return '#06b6d4';
      default: return '#374151';
    }
  };

  // Load GCode for viewer
  const loadGCode = useCallback(async () => {
    if (!uploadedJobId) return;
    
    setGcodeLoading(true);
    setGcodeError(null);
    
    try {
      const result = await printFarmClient.getJobGCode(uploadedJobId, 1, 5000);
      setGcodeData(result);
    } catch (err: any) {
      setGcodeError(err.response?.data?.detail || 'Failed to load G-code');
    } finally {
      setGcodeLoading(false);
    }
  }, [uploadedJobId]);

  // Load GCode when switching to gcode tab
  useEffect(() => {
    if (previewTab === 'gcode' && uploadedJobId && !gcodeData && !gcodeLoading) {
      loadGCode();
    }
  }, [previewTab, uploadedJobId, gcodeData, gcodeLoading, loadGCode]);

  // Filter GCode lines based on search
  const filteredGcodeLines = useMemo(() => {
    if (!gcodeData?.gcode) return [];
    if (!gcodeSearch) return gcodeData.gcode;
    
    const lowerSearch = gcodeSearch.toLowerCase();
    return gcodeData.gcode.filter(line => 
      line.toLowerCase().includes(lowerSearch)
    );
  }, [gcodeData?.gcode, gcodeSearch]);

  // Use sections from backend (already parsed) - direct print mode, no filtering
  const gcodeSections = useMemo((): GCodeSection[] => {
    // Use backend-parsed sections if available
    if (gcodeData?.sections && gcodeData.sections.length > 0) {
      // Direct print mode - return sections as-is without filtering
      return gcodeData.sections;
    }
    return [];
  }, [gcodeData?.sections]);



  useEffect(() => {
    loadQueue();
    loadBucketList();
    // Poll queue every 10 seconds (FDM Monster uses similar intervals)
    const interval = setInterval(loadQueue, 10000);
    return () => clearInterval(interval);
  }, [loadQueue]);

  // Load bucket list
  const loadBucketList = useCallback(async () => {
    if (!printerId) return;
    
    setIsLoadingBucket(true);
    try {
      const items = await printFarmClient.getBucketList(printerId);
      setBucketItems(items);
    } catch (err) {
      console.error('Failed to load bucket list:', err);
    } finally {
      setIsLoadingBucket(false);
    }
  }, [printerId]);

  // Load AMS trays when printer is selected - merge with slot assignments
  const loadAmsTrays = useCallback(async (targetPrinterId: string) => {
    if (!targetPrinterId) {
      setAmsTrays([]);
      return;
    }
    
    try {
      // Load both AMS trays and slot assignments
      const [amsResponse, slotsResponse] = await Promise.all([
        printFarmClient.getAmsTrays(targetPrinterId),
        printFarmClient.getSlotAssignments(targetPrinterId).catch(() => ({ slots: {} as Record<number, any> }))
      ]);
      
      const trays = amsResponse.trays || [];
      const slots: Record<number, any> = slotsResponse.slots || {};
      
      // Helper to convert RRGGBBAA to #RRGGBB
      const formatColor = (colorHex: string | null | undefined): string => {
        if (!colorHex) return '#808080';
        // Remove # if present
        const hex = colorHex.replace('#', '');
        // Take first 6 characters (RGB), ignore alpha
        const rgb = hex.substring(0, 6);
        return `#${rgb}`;
      };
      
      // Merge slot assignment info into trays
      const mergedTrays = trays.map((tray: AmsTray) => {
        const assignment = slots[tray.slot];
        if (assignment) {
          return {
            ...tray,
            name: assignment.name || tray.name,
            type: assignment.material_type || tray.type,
            brand: assignment.brand,
            color: formatColor(assignment.color_hex) || tray.color,
            nozzle_temp_default: assignment.nozzle_temp_default,
            bed_temp_default: assignment.bed_temp_default,
            remaining_grams: assignment.remaining_grams,
            spool_weight: assignment.spool_weight,
            filament_id: assignment.filament_id,  // Store filament_id for temperature overrides
          };
        }
        return tray;
      });
      
      setAmsTrays(mergedTrays);
      
      // Save currently loaded tray from printer (tray_now)
      const trayNow = amsResponse.tray_now ?? 255;
      setCurrentlyLoadedSlot(trayNow);
      
      // Default to first loaded tray (or currently loaded if available)
      if (mergedTrays.length > 0) {
        // Prefer currently loaded slot if it exists and is not empty
        if (trayNow !== 255 && trayNow !== 254) {
          const loadedTray = mergedTrays.find((t: AmsTray) => t.slot === trayNow && !t.empty);
          if (loadedTray) {
            setSelectedAmsSlot(loadedTray.slot);
            if (loadedTray.nozzle_temp_default) {
              setDisplayNozzleTemp(loadedTray.nozzle_temp_default);
            }
            if (loadedTray.bed_temp_default) {
              setDisplayBedTemp(loadedTray.bed_temp_default);
            }
            return; // Exit early, we found the loaded tray
          }
        }
        
        // Fallback to first non-empty tray
        const firstLoaded = mergedTrays.find((t: AmsTray) => !t.empty);
        if (firstLoaded) {
          setSelectedAmsSlot(firstLoaded.slot);
          // Set initial temperature from first loaded tray
          if (firstLoaded.nozzle_temp_default) {
            setDisplayNozzleTemp(firstLoaded.nozzle_temp_default);
          }
          if (firstLoaded.bed_temp_default) {
            setDisplayBedTemp(firstLoaded.bed_temp_default);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load AMS trays:', err);
      setAmsTrays([]);
      setCurrentlyLoadedSlot(255);
    }
  }, []);

  // Load presets and select default
  // No presets - direct print mode

  useEffect(() => {
    if (selectedUploadPrinter) {
      loadAmsTrays(selectedUploadPrinter);
    }
  }, [selectedUploadPrinter, loadAmsTrays]);

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const handleStartNext = async () => {
    try {
      setIsStartingJob(true);
      setPrinterUploadProgress({
        percent: 0,
        bytes_sent: 0,
        total_bytes: 0,
        filename: '',
        status: 'starting'
      });
      await printFarmClient.startNextJob(printerId);
      setMessage({ type: 'success', text: '📤 Uploading to printer...' });
      // Don't call loadQueue here - let WebSocket handle completion
      onRefresh?.();
    } catch (err: any) {
      setIsStartingJob(false);
      setPrinterUploadProgress(null);
      setMessage({ type: 'error', text: err.message || 'Failed to start job' });
    }
  };

  const handleRemove = async (queueId: number, itemStatus?: string) => {
    const isStuck = itemStatus === 'running' && printerStatus !== 'printing';
    const confirmMsg = isStuck
      ? '⚠️ Queue status is "running" but printer is not printing.\nForce remove this stuck job?'
      : 'Remove this job from queue?';
    
    if (!window.confirm(confirmMsg)) return;
    
    try {
      await printFarmClient.removeFromQueue(queueId);
      setMessage({ type: 'success', text: isStuck ? 'Stuck job removed from queue' : 'Job removed from queue' });
      loadQueue();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to remove job' });
    }
  };

  const handleMoveUp = async (queueId: number, currentPosition: number) => {
    if (currentPosition <= 1) return;
    
    try {
      await printFarmClient.updateQueuePosition(queueId, currentPosition - 1);
      loadQueue();
    } catch (err) {
      console.error('Failed to move job:', err);
    }
  };

  const handleMoveDown = async (queueId: number, currentPosition: number) => {
    try {
      await printFarmClient.updateQueuePosition(queueId, currentPosition + 1);
      loadQueue();
    } catch (err) {
      console.error('Failed to move job:', err);
    }
  };

  // Edit queue item
  const handleEditQueueItem = async (queueId: number) => {
    setEditingQueueId(queueId);
    setShowEditModal(true);
    setIsLoadingEditDetails(true);
    
    try {
      const details = await printFarmClient.getQueueItemDetails(queueId);
      setEditingQueueDetails(details);
      
      // Populate form fields with current values (simplified - 3 checkboxes + AMS)
      setEditAmsSlot(details.ams_slot ?? 0);
      setEditUseAms(details.use_ams ?? true);
      setEditFilamentAlreadyLoaded(details.filament_already_loaded ?? false);
      setEditAutoBedLeveling(details.auto_bed_leveling ?? true);
      setEditFlowCalibration(details.flow_calibration ?? false);
      setEditTimelapse(details.timelapse ?? false);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load queue item details' });
      setShowEditModal(false);
    } finally {
      setIsLoadingEditDetails(false);
    }
  };

  const handleSaveEditSettings = async () => {
    if (!editingQueueId) return;
    
    setIsSavingEdit(true);
    try {
      await printFarmClient.updateQueueSettings(editingQueueId, {
        ams_slot: editAmsSlot,
        use_ams: editUseAms,
        filament_already_loaded: editFilamentAlreadyLoaded,
        auto_bed_leveling: editAutoBedLeveling,
        flow_calibration: editFlowCalibration,
        timelapse: editTimelapse
      });
      
      setMessage({ type: 'success', text: 'Queue item settings updated (3 checkboxes only)' });
      setShowEditModal(false);
      setEditingQueueId(null);
      setEditingQueueDetails(null);
      loadQueue();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update settings' });
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleCloseEditModal = () => {
    setShowEditModal(false);
    setEditingQueueId(null);
    setEditingQueueDetails(null);
  };

  // Bucket List handlers
  const handleMoveToBucket = async (queueId: number) => {
    try {
      await printFarmClient.moveQueueToBucket(queueId);
      setMessage({ type: 'success', text: '📦 Job saved to bucket list' });
      loadQueue();
      loadBucketList();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to move to bucket' });
    }
  };

  const handleMoveToQueue = async (bucketId: number) => {
    try {
      await printFarmClient.moveBucketToQueue(bucketId, printerId);
      setMessage({ type: 'success', text: '✅ Job moved to queue' });
      loadQueue();
      loadBucketList();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to move to queue' });
    }
  };

  const handleRemoveFromBucket = async (bucketId: number) => {
    if (!window.confirm('Remove this job from bucket list?')) return;
    
    try {
      await printFarmClient.removeFromBucket(bucketId, false);
      setMessage({ type: 'success', text: 'Removed from bucket list' });
      loadBucketList();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to remove from bucket' });
    }
  };

  // Upload handlers
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validExtensions = ['.3mf', '.stl'];
      const fileName = file.name.toLowerCase();
      const isValid = validExtensions.some(ext => fileName.endsWith(ext));
      if (isValid) {
        setSelectedFile(file);
      } else {
        setMessage({ type: 'error', text: 'Please select a .3mf or .stl file' });
        setSelectedFile(null);
      }
    }
  };

  // Step 1: Upload file and show preview
  const handleUpload = async () => {
    if (!selectedFile) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    try {
      // Upload file to server
      const job = await printFarmClient.uploadJob(selectedFile, loopCount, (percent) => {
        setUploadProgress(percent);
      });
      
      // Store job info for preview
      setUploadedJobId(job.jobId);
      setUploadedJobName(job.jobName);
      
      // Wait a bit for file to be fully written on server before fetching metadata
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Fetch metadata for preview with retry
      setIsLoadingMetadata(true);
      let retries = 3;
      let metadata = null;
      while (retries > 0) {
        try {
          metadata = await printFarmClient.getJobMetadata(job.jobId);
          break;
        } catch (err) {
          retries--;
          if (retries > 0) {
            await new Promise(resolve => setTimeout(resolve, 500));
          } else {
            console.warn('Could not load metadata after retries:', err);
          }
        }
      }
      setJobMetadata(metadata);
      setThumbnailUrl(printFarmClient.getJobThumbnailUrl(job.jobId));
      setIsLoadingMetadata(false);
      
      // Fetch print preview steps
      try {
        const preview = await printFarmClient.getPrintPreview(job.jobId);
        setPrintPreview(preview);
      } catch (err) {
        console.warn('Could not load print preview:', err);
        setPrintPreview(null);
      }
      
      // Set automation defaults based on file metadata
      if (metadata) {
        // Store original temperatures from file
        if (metadata.nozzle_temp) {
          setOriginalNozzleTemp(metadata.nozzle_temp);
          setDisplayNozzleTemp(metadata.nozzle_temp);
        }
        if (metadata.bed_temp) {
          setOriginalBedTemp(metadata.bed_temp);
          setDisplayBedTemp(metadata.bed_temp);
        }
        
        // NOTE: Automation settings are now derived from presets, not individual state
        // The metadata detection values are logged for debugging but not applied to state
        console.log('📋 File automation settings (from metadata):', {
          has_bed_leveling: metadata.has_bed_leveling,
          has_flow_calibration: metadata.has_flow_calibration,
          has_vibration_test: metadata.has_vibration_test,
          has_clean_nozzle: metadata.has_clean_nozzle,
          has_auto_eject: metadata.has_auto_eject,
          has_startup_sound: metadata.has_startup_sound,
          has_end_sound: metadata.has_end_sound,
          has_timelapse: metadata.has_timelapse,
        });
      }
      
      // Show preview modal
      setShowPreview(true);
      setPreviewTab('job'); // Reset to job tab
      setGcodeData(null);   // Clear previous gcode data
      setGcodeError(null);
      setGcodeSearch('');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      
    } catch (err: any) {
      let errorText = 'Failed to upload job';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        errorText = typeof detail === 'string' ? detail : (detail.msg || 'Failed to upload job');
      } else if (err.message) {
        errorText = err.message;
      }
      setMessage({ type: 'error', text: errorText });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Step 2a: Add to queue (confirm)
  const handleAddToQueue = async () => {
    if (!uploadedJobId || !selectedUploadPrinter) {
      setMessage({ type: 'error', text: 'Please select a printer' });
      return;
    }
    
    try {
      // Update loop count in database if changed
      await printFarmClient.updateJobLoopCount(uploadedJobId, loopCount);
      
      const amsMapping = useAms ? `[${selectedAmsSlot}]` : '';
      
      // Auto-detect if filament is already loaded in nozzle
      // If the selected AMS slot matches the currently loaded slot, skip loading sequence
      const filamentAlreadyLoaded = useAms && selectedAmsSlot === currentlyLoadedSlot && currentlyLoadedSlot !== 255;
      
      if (filamentAlreadyLoaded) {
        console.log(`✅ Filament already loaded in slot ${selectedAmsSlot}, will skip AMS loading sequence`);
      }
      
      // Get filament_id from selected AMS slot for temperature overrides
      const selectedTray = amsTrays.find(t => t.slot === selectedAmsSlot);
      const filamentId = useAms && selectedTray?.filament_id ? selectedTray.filament_id : undefined;
      
      if (filamentId) {
        console.log(`📋 Using filament_id ${filamentId} for temperature overrides from slot ${selectedAmsSlot}`);
      }
      
      // Send automation settings per job
      await printFarmClient.addJobToQueue(uploadedJobId, selectedUploadPrinter, {
        amsSlot: selectedAmsSlot,
        amsMapping: amsMapping,
        useAms: useAms,
        filamentAlreadyLoaded: filamentAlreadyLoaded,
        filamentId: filamentId,
        skip_preprocessing: false,  // Enable preprocessing with custom settings
        autoBedLeveling: autoBedLeveling,
        flowCalibration: flowCalibration,
        timelapse: timelapse
      });
      
      const printerName = printers.find(p => p.printerId === selectedUploadPrinter)?.printerName || 'printer';
      const filamentInfo = selectedTray ? ` (Slot ${selectedAmsSlot}: ${selectedTray.type})` : '';
      const skipLoadInfo = filamentAlreadyLoaded ? ' • Skip AMS Load' : '';
      
      setMessage({ 
        type: 'success', 
        text: `✅ "${uploadedJobName}" added to ${printerName} queue${filamentInfo}${skipLoadInfo}` 
      });
      
      // Reset preview state
      setShowPreview(false);
      setUploadedJobId(null);
      setUploadedJobName('');
      setJobMetadata(null);
      setThumbnailUrl(null);
      setLoopCount(1);
      
      // Reset temperature display
      setDisplayNozzleTemp(null);
      setDisplayBedTemp(null);
      setOriginalNozzleTemp(null);
      setOriginalBedTemp(null);
      
      // Reset automation settings to defaults
      setAutoBedLeveling(true);
      setFlowCalibration(false);
      setTimelapse(false);
      
      loadQueue();
      onRefresh?.(); // Refresh jobs list to show updated loop counts
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to add to queue' });
    }
  };

  // Step 2b: Cancel and delete file
  const handleCancelUpload = async () => {
    if (uploadedJobId) {
      try {
        await printFarmClient.deleteJob(uploadedJobId);
        setMessage({ type: 'success', text: 'Upload cancelled, file deleted' });
      } catch (err) {
        console.warn('Failed to delete job:', err);
      }
    }
    
    // Reset preview state
    setShowPreview(false);
    setUploadedJobId(null);
    setUploadedJobName('');
    setJobMetadata(null);
    setThumbnailUrl(null);
    
    // Reset temperature display
    setDisplayNozzleTemp(null);
    setDisplayBedTemp(null);
    setOriginalNozzleTemp(null);
    setOriginalBedTemp(null);
  };

  // Format time helper
  const formatTime = (seconds: number | null) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'running':
        return { backgroundColor: '#fef3c7', color: '#b45309' };
      case 'pending':
        return { backgroundColor: '#dbeafe', color: '#1d4ed8' };
      case 'uploading':
        return { backgroundColor: '#e0e7ff', color: '#4338ca' };
      case 'starting':
        return { backgroundColor: '#fef9c3', color: '#a16207' };
      case 'completed':
        return { backgroundColor: '#d1fae5', color: '#047857' };
      case 'failed':
      case 'error':
        return { backgroundColor: '#fee2e2', color: '#b91c1c' };
      default:
        return { backgroundColor: '#f3f4f6', color: '#6b7280' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* SD Card Files Section - Displayed Above Upload */}
      <PrinterFilesTab printerStatus={undefined} />
      
      {/* Upload Section */}
      {showUpload && (
        <div style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          padding: '20px',
        }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
            📤 Upload New Job
          </h3>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap' }}>
            {/* File Input */}
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: '#6b7280', marginBottom: '6px', fontWeight: 500 }}>
                📁 Select File (.3mf, .stl)
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".3mf,.stl"
                onChange={handleFileChange}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: '14px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  backgroundColor: '#f9fafb',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            
            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={isUploading || !selectedFile}
              style={{
                padding: '12px 28px',
                fontSize: '14px',
                fontWeight: 600,
                color: '#ffffff',
                backgroundColor: selectedFile ? '#2563eb' : '#9ca3af',
                border: 'none',
                borderRadius: '8px',
                cursor: selectedFile ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                whiteSpace: 'nowrap',
              }}
            >
              {isUploading ? '⏳ Uploading...' : '📤 Upload'}
            </button>
          </div>
          
          {/* Upload Progress Bar */}
          {isUploading && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500 }}>Uploading...</span>
                <span style={{ fontSize: '13px', color: '#2563eb', fontWeight: 600 }}>{uploadProgress}%</span>
              </div>
              <div style={{ 
                width: '100%', 
                height: '8px', 
                backgroundColor: '#e5e7eb', 
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${uploadProgress}%`,
                  height: '100%',
                  backgroundColor: uploadProgress === 100 ? '#10b981' : '#2563eb',
                  transition: 'width 0.3s ease, background-color 0.3s ease',
                  borderRadius: '4px'
                }} />
              </div>
              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '6px' }}>
                {uploadProgress < 100 ? '📤 Uploading file to server...' : '✓ Processing...'}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="queue-stats-grid">
          <div style={{
            padding: '16px',
            backgroundColor: '#ffffff',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#1f2937' }}>
              {stats.total_items}
            </div>
            <div style={{ fontSize: '12px', color: '#6b7280' }}>Total Jobs</div>
          </div>
          
          <div style={{
            padding: '16px',
            backgroundColor: '#dbeafe',
            borderRadius: '10px',
            border: '1px solid #93c5fd',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#1d4ed8' }}>
              {stats.pending_items}
            </div>
            <div style={{ fontSize: '12px', color: '#1d4ed8' }}>Pending</div>
          </div>
          
          <div style={{
            padding: '16px',
            backgroundColor: '#fef3c7',
            borderRadius: '10px',
            border: '1px solid #fcd34d',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#b45309' }}>
              {stats.running_items}
            </div>
            <div style={{ fontSize: '12px', color: '#b45309' }}>Running</div>
          </div>
          
          <div style={{
            padding: '16px',
            backgroundColor: '#d1fae5',
            borderRadius: '10px',
            border: '1px solid #6ee7b7',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#047857' }}>
              {stats.completed_items}
            </div>
            <div style={{ fontSize: '12px', color: '#047857' }}>Completed</div>
          </div>
        </div>
      )}

      {/* Message Toast */}
      {message && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: message.type === 'success' ? '#d1fae5' : '#fee2e2',
          color: message.type === 'success' ? '#047857' : '#b91c1c',
          fontSize: '14px',
        }}>
          {message.type === 'success' ? '✓' : '✕'} {message.text}
        </div>
      )}

      {/* Printer Upload Progress Bar */}
      {(isStartingJob || printerUploadProgress) && (
        <div style={{
          padding: '16px',
          backgroundColor: '#f0f9ff',
          borderRadius: '12px',
          border: '1px solid #bae6fd',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#0369a1' }}>
              {printerUploadProgress?.status === 'starting' && '📋 Preparing...'}
              {printerUploadProgress?.status === 'uploading' && `📤 Uploading to printer: ${printerUploadProgress.filename}`}
              {printerUploadProgress?.status === 'complete' && '✅ Upload complete'}
              {printerUploadProgress?.status === 'starting_print' && '🖨️ Starting print...'}
              {printerUploadProgress?.status === 'print_started' && '✅ Print started!'}
              {printerUploadProgress?.status === 'failed' && '❌ Upload failed'}
              {printerUploadProgress?.status === 'print_failed' && '❌ Failed to start print'}
              {!printerUploadProgress?.status && '⏳ Connecting...'}
            </span>
            <span style={{ fontSize: '14px', fontWeight: 700, color: '#0369a1' }}>
              {printerUploadProgress?.percent || 0}%
            </span>
          </div>
          
          <div style={{
            width: '100%',
            height: '10px',
            backgroundColor: '#e0f2fe',
            borderRadius: '5px',
            overflow: 'hidden',
          }}>
            <div style={{
              width: `${printerUploadProgress?.percent || 0}%`,
              height: '100%',
              backgroundColor: printerUploadProgress?.status === 'failed' || printerUploadProgress?.status === 'print_failed' 
                ? '#ef4444' 
                : printerUploadProgress?.status === 'print_started' 
                  ? '#10b981' 
                  : '#0ea5e9',
              transition: 'width 0.3s ease, background-color 0.3s ease',
              borderRadius: '5px',
            }} />
          </div>
          
          {printerUploadProgress && printerUploadProgress.total_bytes > 0 && (
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
              {((printerUploadProgress.bytes_sent || 0) / (1024 * 1024)).toFixed(2)} MB / {((printerUploadProgress.total_bytes || 0) / (1024 * 1024)).toFixed(2)} MB
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        <button
          onClick={handleStartNext}
          disabled={!stats?.pending_items || isStartingJob || (stats?.running_items ?? 0) > 0}
          style={{
            padding: '12px 24px',
            borderRadius: '8px',
            border: 'none',
            backgroundColor: stats?.pending_items && !isStartingJob && (stats?.running_items ?? 0) === 0 ? '#10b981' : '#e5e7eb',
            color: stats?.pending_items && !isStartingJob && (stats?.running_items ?? 0) === 0 ? '#ffffff' : '#9ca3af',
            fontSize: '14px',
            fontWeight: 500,
            cursor: stats?.pending_items && !isStartingJob && (stats?.running_items ?? 0) === 0 ? 'pointer' : 'not-allowed',
          }}
        >
          {isStartingJob ? '⏳ Starting...' : (stats?.running_items ?? 0) > 0 ? '🔄 Job Running...' : '▶ Start Next Job'}
        </button>
      </div>

      {/* Queue List */}
      <div className="queue-table" style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div className="queue-header" style={{
          backgroundColor: '#f9fafb',
          borderBottom: '1px solid #e5e7eb',
          fontSize: '12px',
          fontWeight: 600,
          color: '#6b7280',
          textTransform: 'uppercase',
        }}>
          <div>#</div>
          <div>Job Name</div>
          <div>Loop</div>
          <div>Status</div>
          <div>Actions</div>
        </div>

        {/* Queue Items */}
        {queueItems.length === 0 ? (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#6b7280',
          }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>📋</div>
            <div>Queue is empty</div>
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              Upload a job and add it to the queue
            </div>
          </div>
        ) : (
          queueItems.map((item, index) => (
            <div
              key={item.queue_id}
              className="queue-row"
              style={{
                borderBottom: index < queueItems.length - 1 ? '1px solid #e5e7eb' : 'none',
                backgroundColor: item.status === 'running' ? '#fffbeb' : '#ffffff',
              }}
            >
              {/* Position */}
              <div style={{ fontWeight: 600, color: '#1f2937' }}>
                {item.status === 'running' ? '▶️' : item.position_in_queue}
              </div>
              
              {/* Job Name */}
              <div>
                <div style={{ fontWeight: 500, color: '#1f2937' }}>{item.job_name}</div>
                <div style={{ fontSize: '11px', color: '#9ca3af', fontFamily: 'monospace' }}>
                  ID: {item.job_id}
                </div>
              </div>
              
              {/* Loop Progress */}
              <div style={{ fontSize: '13px', color: '#6b7280' }}>
                {item.current_loop} / {item.loop_count}
              </div>
              
              {/* Status Badge */}
              <div>
                <span style={{
                  padding: '4px 10px',
                  borderRadius: '20px',
                  fontSize: '11px',
                  fontWeight: 500,
                  ...getStatusStyle(item.status),
                }}>
                  {item.status}
                </span>
              </div>
              
              {/* Actions - 2x3 grid */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: '28px 28px 28px', 
                gridTemplateRows: '26px 26px',
                gap: '3px',
              }}>
                {/* Row 1: Up, Down, Bucket */}
                <button
                  onClick={() => handleMoveUp(item.queue_id, item.position_in_queue)}
                  disabled={item.position_in_queue <= 1 || item.status !== 'pending'}
                  style={{
                    padding: '0',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: '#f3f4f6',
                    color: '#6b7280',
                    fontSize: '13px',
                    cursor: item.position_in_queue <= 1 || item.status !== 'pending' ? 'not-allowed' : 'pointer',
                    opacity: item.position_in_queue <= 1 || item.status !== 'pending' ? 0.4 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title="Move Up"
                >
                  ↑
                </button>
                <button
                  onClick={() => handleMoveDown(item.queue_id, item.position_in_queue)}
                  disabled={item.position_in_queue >= queueItems.length || item.status !== 'pending'}
                  style={{
                    padding: '0',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: '#f3f4f6',
                    color: '#6b7280',
                    fontSize: '13px',
                    cursor: item.position_in_queue >= queueItems.length || item.status !== 'pending' ? 'not-allowed' : 'pointer',
                    opacity: item.position_in_queue >= queueItems.length || item.status !== 'pending' ? 0.4 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title="Move Down"
                >
                  ↓
                </button>
                <button
                  onClick={() => handleMoveToBucket(item.queue_id)}
                  disabled={item.status !== 'pending'}
                  style={{
                    padding: '0',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: item.status === 'pending' ? '#fef3c7' : '#f3f4f6',
                    color: item.status === 'pending' ? '#d97706' : '#9ca3af',
                    fontSize: '11px',
                    cursor: item.status === 'pending' ? 'pointer' : 'not-allowed',
                    opacity: item.status === 'pending' ? 1 : 0.4,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title="Save to Bucket List"
                >
                  📦
                </button>
                {/* Row 2: Edit, Delete, empty */}
                <button
                  onClick={() => handleEditQueueItem(item.queue_id)}
                  disabled={item.status !== 'pending'}
                  style={{
                    padding: '0',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: item.status === 'pending' ? '#dbeafe' : '#f3f4f6',
                    color: item.status === 'pending' ? '#1d4ed8' : '#9ca3af',
                    fontSize: '11px',
                    cursor: item.status === 'pending' ? 'pointer' : 'not-allowed',
                    opacity: item.status === 'pending' ? 1 : 0.4,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title="Edit Settings"
                >
                  ✏️
                </button>
                <button
                  onClick={() => handleRemove(item.queue_id, item.status)}
                  disabled={item.status === 'running' && printerStatus === 'printing'}
                  style={{
                    padding: '0',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: item.status === 'running' && printerStatus !== 'printing'
                      ? '#fff7ed'  // orange-tinted when stuck
                      : item.status !== 'running'
                      ? '#fee2e2'
                      : '#f3f4f6',
                    color: item.status === 'running' && printerStatus !== 'printing'
                      ? '#ea580c'  // orange when stuck
                      : item.status !== 'running'
                      ? '#b91c1c'
                      : '#9ca3af',
                    fontSize: '13px',
                    cursor: item.status === 'running' && printerStatus === 'printing' ? 'not-allowed' : 'pointer',
                    opacity: item.status === 'running' && printerStatus === 'printing' ? 0.4 : 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                  title={item.status === 'running' && printerStatus !== 'printing'
                    ? 'Force Remove (job stuck - printer not printing)'
                    : item.status === 'running'
                    ? 'Cannot remove while printing'
                    : 'Remove'
                  }
                >
                  {item.status === 'running' && printerStatus !== 'printing' ? '⚠️' : '✕'}
                </button>
                <div></div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Bucket List Section */}
      <div style={{
        backgroundColor: '#fffbeb',
        borderRadius: '12px',
        padding: '16px',
        marginTop: '20px',
        border: '1px solid #fbbf24',
      }}>
        <div 
          onClick={() => setShowBucketSection(!showBucketSection)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '20px' }}>📦</span>
            <span style={{ fontWeight: 600, color: '#92400e' }}>
              Bucket List ({bucketItems.length})
            </span>
            <span style={{ fontSize: '12px', color: '#b45309' }}>
              Jobs saved for later
            </span>
          </div>
          <span style={{ fontSize: '16px', color: '#b45309' }}>
            {showBucketSection ? '▼' : '▶'}
          </span>
        </div>

        {showBucketSection && (
          <div style={{ marginTop: '12px' }}>
            {isLoadingBucket ? (
              <div style={{ textAlign: 'center', padding: '20px', color: '#b45309' }}>
                Loading bucket list...
              </div>
            ) : bucketItems.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '24px', 
                color: '#92400e',
                backgroundColor: '#fef3c7',
                borderRadius: '8px',
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>📦</div>
                <div>No saved jobs yet</div>
                <div style={{ fontSize: '12px', marginTop: '4px', color: '#b45309' }}>
                  Use the 📦 button on pending queue items to save them here
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {bucketItems.map((item: any) => (
                  <div
                    key={item.bucket_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px',
                      backgroundColor: '#ffffff',
                      borderRadius: '8px',
                      border: '1px solid #fde68a',
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ 
                        fontWeight: 500, 
                        color: '#1f2937',
                        fontSize: '14px',
                        marginBottom: '4px',
                      }}>
                        {item.job?.name || 'Unknown Job'}
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        gap: '12px', 
                        flexWrap: 'wrap',
                        fontSize: '11px', 
                        color: '#6b7280' 
                      }}>
                        {item.ams_slot && (
                          <span>AMS: Slot {item.ams_slot}</span>
                        )}
                        {item.loop_count > 1 && (
                          <span>Loop: {item.loop_count}x</span>
                        )}
                        {item.auto_bed_leveling && <span>🔧 Bed Level</span>}
                        {item.flow_calibration && <span>💧 Flow Cal</span>}
                        {item.notes && (
                          <span style={{ color: '#92400e' }}>📝 {item.notes}</span>
                        )}
                      </div>
                      <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '4px' }}>
                        Saved: {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => handleMoveToQueue(item.bucket_id)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: 'none',
                          backgroundColor: '#10b981',
                          color: '#ffffff',
                          fontSize: '12px',
                          fontWeight: 500,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        title="Move to Queue"
                      >
                        ▶ Queue
                      </button>
                      <button
                        onClick={() => handleRemoveFromBucket(item.bucket_id)}
                        style={{
                          padding: '6px 10px',
                          borderRadius: '6px',
                          border: 'none',
                          backgroundColor: '#fee2e2',
                          color: '#b91c1c',
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                        title="Remove from Bucket"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Preview Modal - After Upload */}
      {showPreview && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            width: '90%',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          }}>
            {/* Header */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '16px',
              paddingBottom: '16px',
              borderBottom: '1px solid #e5e7eb',
            }}>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#1f2937' }}>
                📄 File Preview
              </h2>
              <button
                onClick={handleCancelUpload}
                style={{
                  border: 'none',
                  background: 'none',
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: '#6b7280',
                }}
              >
                ✕
              </button>
            </div>

            {/* Tab Content - Now always shows job info (tabs removed) */}
            {true && (
              <>
                {/* File Info */}
                <div style={{
                  backgroundColor: '#f9fafb',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '20px',
                }}>
                  <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                marginBottom: '12px',
              }}>
                <span style={{ fontSize: '32px' }}>📦</span>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
                    {uploadedJobName}
                  </div>
                  <div style={{ fontSize: '13px', color: '#6b7280' }}>
                    {jobMetadata?.file_size_mb ? `${jobMetadata.file_size_mb} MB` : ''} • {jobMetadata?.file_type?.toUpperCase() || '3MF'}
                  </div>
                </div>
              </div>
              
              {/* Thumbnail Preview */}
              {thumbnailUrl && (
                <div style={{
                  marginTop: '12px',
                  display: 'flex',
                  justifyContent: 'center',
                }}>
                  <img 
                    src={thumbnailUrl}
                    alt="Model Preview"
                    style={{
                      maxWidth: '100%',
                      maxHeight: '200px',
                      borderRadius: '8px',
                      objectFit: 'contain',
                      backgroundColor: '#e5e7eb',
                    }}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              )}
            </div>

            {/* Metadata Grid */}
            {isLoadingMetadata ? (
              <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>
                Loading file details...
              </div>
            ) : jobMetadata ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '12px',
                marginBottom: '20px',
              }}>
                {/* Estimated Time */}
                <div style={{
                  backgroundColor: '#fef3c7',
                  borderRadius: '8px',
                  padding: '12px',
                }}>
                  <div style={{ fontSize: '12px', color: '#92400e', marginBottom: '4px' }}>
                    ⏱️ Estimated Time
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: '#b45309' }}>
                    {jobMetadata.estimated_time || formatTime(jobMetadata.estimated_time_seconds)}
                  </div>
                </div>

                {/* Filament Used */}
                <div style={{
                  backgroundColor: '#dbeafe',
                  borderRadius: '8px',
                  padding: '12px',
                }}>
                  <div style={{ fontSize: '12px', color: '#1e40af', marginBottom: '4px' }}>
                    🧵 Filament Used
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: '#1d4ed8' }}>
                    {jobMetadata.filament_used_g ? `${jobMetadata.filament_used_g.toFixed(1)}g` : 'Unknown'}
                  </div>
                </div>

                {/* Layer Count */}
                <div style={{
                  backgroundColor: '#f3e8ff',
                  borderRadius: '8px',
                  padding: '12px',
                }}>
                  <div style={{ fontSize: '12px', color: '#6b21a8', marginBottom: '4px' }}>
                    📐 Layers
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: '#7c3aed' }}>
                    {jobMetadata.layer_count || 'Unknown'}
                  </div>
                </div>

                {/* Layer Height */}
                <div style={{
                  backgroundColor: '#dcfce7',
                  borderRadius: '8px',
                  padding: '12px',
                }}>
                  <div style={{ fontSize: '12px', color: '#166534', marginBottom: '4px' }}>
                    📏 Layer Height
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: '#15803d' }}>
                    {jobMetadata.layer_height ? `${jobMetadata.layer_height}mm` : 'Unknown'}
                  </div>
                </div>

                {/* Temperatures */}
                {(jobMetadata.nozzle_temp || jobMetadata.bed_temp) && (
                  <>
                    <div style={{
                      backgroundColor: '#fee2e2',
                      borderRadius: '8px',
                      padding: '12px',
                    }}>
                      <div style={{ fontSize: '12px', color: '#991b1b', marginBottom: '4px' }}>
                        🔥 Nozzle Temp
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 600, color: '#dc2626' }}>
                        {jobMetadata.nozzle_temp ? `${jobMetadata.nozzle_temp}°C` : 'Unknown'}
                      </div>
                    </div>

                    <div style={{
                      backgroundColor: '#ffedd5',
                      borderRadius: '8px',
                      padding: '12px',
                    }}>
                      <div style={{ fontSize: '12px', color: '#9a3412', marginBottom: '4px' }}>
                        🛏️ Bed Temp
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 600, color: '#ea580c' }}>
                        {jobMetadata.bed_temp ? `${jobMetadata.bed_temp}°C` : 'Unknown'}
                      </div>
                    </div>
                  </>
                )}

                {/* Filament Type */}
                {jobMetadata.filament_type && (
                  <div style={{
                    backgroundColor: '#f0fdf4',
                    borderRadius: '8px',
                    padding: '12px',
                    gridColumn: 'span 2',
                  }}>
                    <div style={{ fontSize: '12px', color: '#166534', marginBottom: '4px' }}>
                      🎨 Filament
                    </div>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '8px',
                    }}>
                      {jobMetadata.filament_color && (
                        <div style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          backgroundColor: jobMetadata.filament_color,
                          border: '2px solid #e5e7eb',
                        }} />
                      )}
                      <span style={{ fontSize: '16px', fontWeight: 600, color: '#15803d' }}>
                        {jobMetadata.filament_type}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ 
                textAlign: 'center', 
                padding: '20px', 
                color: '#6b7280',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                marginBottom: '20px',
              }}>
                Could not extract metadata from file
              </div>
            )}

            {/* ==================== AMS FILAMENT SELECTION ==================== */}
            <div style={{
              backgroundColor: '#fffbeb',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '20px',
              border: '1px solid #fde68a',
            }}>
              {/* AMS FILAMENT SELECTION */}
              
              {/* Loop Count Setting - Can be edited before adding to queue */}
              <div style={{
                marginBottom: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid #fde68a',
              }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '14px', 
                  fontWeight: 600, 
                  color: '#92400e',
                  marginBottom: '8px',
                }}>
                  🔄 Print Loops (berapa kali print)
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={loopCount}
                  onChange={(e) => setLoopCount(parseInt(e.target.value) || 1)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    fontSize: '14px',
                    border: '1px solid #fbbf24',
                    borderRadius: '8px',
                    backgroundColor: '#ffffff',
                    textAlign: 'center',
                    fontWeight: 600,
                    boxSizing: 'border-box',
                  }}
                />
                <div style={{ 
                  marginTop: '8px', 
                  fontSize: '12px', 
                  color: '#b45309',
                  textAlign: 'center',
                }}>
                  💡 File akan di-print otomatis sebanyak <strong>{loopCount}x</strong>
                </div>
              </div>

              <div style={{ 
                fontSize: '14px', 
                fontWeight: 600, 
                color: '#92400e',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                🎨 Select Filament
              </div>
              
              {/* AMS Toggle */}
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 12px',
                backgroundColor: useAms ? '#fef3c7' : '#ffffff',
                borderRadius: '8px',
                cursor: 'pointer',
                border: useAms ? '2px solid #f59e0b' : '1px solid #e5e7eb',
                marginBottom: '12px',
              }}>
                <input
                  type="checkbox"
                  checked={useAms}
                  onChange={(e) => setUseAms(e.target.checked)}
                  style={{ width: '18px', height: '18px', accentColor: '#f59e0b' }}
                />
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: useAms ? '#b45309' : '#374151' }}>
                    🗃️ Use AMS Lite
                  </div>
                  <div style={{ fontSize: '11px', color: useAms ? '#d97706' : '#6b7280' }}>
                    {useAms ? 'Select filament from AMS slots' : 'Using external spool'}
                  </div>
                </div>
              </label>
              
              {/* AMS Slot Selection */}
              {useAms && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '8px',
                }}>
                  {amsTrays.filter(t => !t.is_external).map((tray) => (
                    <button
                      key={tray.slot}
                      onClick={() => {
                        setSelectedAmsSlot(tray.slot);
                        // Update temperature display when slot is selected
                        if (tray.nozzle_temp_default) {
                          setDisplayNozzleTemp(tray.nozzle_temp_default);
                        }
                        if (tray.bed_temp_default) {
                          setDisplayBedTemp(tray.bed_temp_default);
                        }
                      }}
                      disabled={tray.empty}
                      style={{
                        padding: '12px 8px',
                        borderRadius: '8px',
                        border: selectedAmsSlot === tray.slot 
                          ? '3px solid #f59e0b' 
                          : tray.empty 
                            ? '1px dashed #d1d5db' 
                            : '1px solid #e5e7eb',
                        backgroundColor: selectedAmsSlot === tray.slot 
                          ? '#fef3c7' 
                          : tray.empty 
                            ? '#f9fafb' 
                            : '#ffffff',
                        cursor: tray.empty ? 'not-allowed' : 'pointer',
                        opacity: tray.empty ? 0.5 : 1,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      {/* Color Circle */}
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        backgroundColor: tray.empty ? '#e5e7eb' : tray.color,
                        border: tray.color?.toLowerCase() === '#ffffff' || tray.empty
                          ? '2px solid #d1d5db' 
                          : '2px solid transparent',
                        boxShadow: selectedAmsSlot === tray.slot 
                          ? '0 0 0 3px rgba(245, 158, 11, 0.3)' 
                          : 'none',
                      }} />
                      
                      {/* Slot Number */}
                      <div style={{ 
                        fontSize: '11px', 
                        fontWeight: 600,
                        color: selectedAmsSlot === tray.slot ? '#b45309' : '#6b7280',
                      }}>
                        Slot {tray.slot + 1}
                        {/* Show "IN NOZZLE" badge if this slot is currently loaded */}
                        {currentlyLoadedSlot === tray.slot && (
                          <span style={{
                            marginLeft: '4px',
                            fontSize: '8px',
                            backgroundColor: '#22c55e',
                            color: 'white',
                            padding: '1px 4px',
                            borderRadius: '3px',
                            fontWeight: 700,
                          }}>
                            ✓ LOADED
                          </span>
                        )}
                      </div>
                      
                      {/* Filament Brand */}
                      {!tray.empty && tray.brand && (
                        <div style={{ 
                          fontSize: '9px', 
                          color: '#6b7280',
                          textAlign: 'center',
                          fontWeight: 500,
                        }}>
                          {tray.brand}
                        </div>
                      )}
                      
                      {/* Filament Type */}
                      <div style={{ 
                        fontSize: '10px', 
                        color: tray.empty ? '#9ca3af' : '#374151',
                        textAlign: 'center',
                        lineHeight: 1.2,
                        minHeight: '20px',
                        fontWeight: tray.empty ? 400 : 500,
                      }}>
                        {tray.empty ? 'Empty' : (tray.type || tray.name || 'Unknown')}
                      </div>
                      
                      {/* Remain % or grams */}
                      {!tray.empty && (
                        <div style={{ 
                          fontSize: '10px', 
                          color: (tray.remaining_grams && tray.remaining_grams > 200) || tray.remain > 20 ? '#22c55e' : '#ef4444',
                          fontWeight: 500,
                        }}>
                          {tray.remaining_grams ? `${tray.remaining_grams}g` : `${tray.remain}%`}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
              
              {/* Filament Already Loaded Info */}
              {useAms && selectedAmsSlot === currentlyLoadedSlot && currentlyLoadedSlot !== 255 && (
                <div style={{
                  marginTop: '12px',
                  padding: '10px 12px',
                  backgroundColor: '#dcfce7',
                  borderRadius: '8px',
                  border: '1px solid #22c55e',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}>
                  <span style={{ fontSize: '16px' }}>✅</span>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#166534' }}>
                      Filament Already Loaded
                    </div>
                    <div style={{ fontSize: '11px', color: '#15803d' }}>
                      Skip AMS loading sequence • Faster start • Less filament waste
                    </div>
                  </div>
                </div>
              )}
              
              {/* Selected Filament Temperature Info */}
              {useAms && displayNozzleTemp && displayBedTemp && (
                <div style={{
                  marginTop: '12px',
                  padding: '10px 12px',
                  backgroundColor: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb',
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '20px',
                }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#6b7280' }}>🔥 Nozzle</div>
                    <div style={{ 
                      fontSize: '16px', 
                      fontWeight: 600, 
                      color: displayNozzleTemp !== originalNozzleTemp ? '#f59e0b' : '#dc2626' 
                    }}>
                      {displayNozzleTemp}°C
                      {displayNozzleTemp !== originalNozzleTemp && originalNozzleTemp && (
                        <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '4px' }}>
                          (file: {originalNozzleTemp}°C)
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '11px', color: '#6b7280' }}>🛏️ Bed</div>
                    <div style={{ 
                      fontSize: '16px', 
                      fontWeight: 600, 
                      color: displayBedTemp !== originalBedTemp ? '#f59e0b' : '#ea580c' 
                    }}>
                      {displayBedTemp}°C
                      {displayBedTemp !== originalBedTemp && originalBedTemp && (
                        <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '4px' }}>
                          (file: {originalBedTemp}°C)
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {/* External Spool Info */}
              {!useAms && (
                <div style={{
                  padding: '12px',
                  backgroundColor: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb',
                  textAlign: 'center',
                }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>🧵</div>
                  <div style={{ fontSize: '13px', color: '#6b7280' }}>
                    Using external spool holder
                  </div>
                </div>
              )}
            </div>

            {/* ==================== AUTOMATION SETTINGS ==================== */}
            <div style={{
              backgroundColor: '#f8fafc',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '20px',
              border: '1px solid #e2e8f0',
            }}>
              <div style={{ 
                fontSize: '14px', 
                fontWeight: 600, 
                color: '#1e293b',
                marginBottom: '12px',
              }}>
                ⚙️ Print Settings
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Bed Leveling */}
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px',
                  backgroundColor: autoBedLeveling ? '#dbeafe' : '#ffffff',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: autoBedLeveling ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                  transition: 'all 0.2s',
                }}>
                  <input
                    type="checkbox"
                    checked={autoBedLeveling}
                    onChange={(e) => setAutoBedLeveling(e.target.checked)}
                    style={{ width: '18px', height: '18px', accentColor: '#3b82f6' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: autoBedLeveling ? '#1e40af' : '#374151' }}>
                      📐 Bed Leveling
                    </div>
                    <div style={{ fontSize: '11px', color: autoBedLeveling ? '#3b82f6' : '#6b7280' }}>
                      Auto bed mesh calibration before print
                    </div>
                  </div>
                </label>

                {/* Flow Dynamics Calibration */}
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px',
                  backgroundColor: flowCalibration ? '#dcfce7' : '#ffffff',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: flowCalibration ? '2px solid #22c55e' : '1px solid #e5e7eb',
                  transition: 'all 0.2s',
                }}>
                  <input
                    type="checkbox"
                    checked={flowCalibration}
                    onChange={(e) => setFlowCalibration(e.target.checked)}
                    style={{ width: '18px', height: '18px', accentColor: '#22c55e' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: flowCalibration ? '#15803d' : '#374151' }}>
                      💧 Flow Dynamics Calibration
                    </div>
                    <div style={{ fontSize: '11px', color: flowCalibration ? '#22c55e' : '#6b7280' }}>
                      Optimize extrusion flow rate
                    </div>
                  </div>
                </label>

                {/* Timelapse */}
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px',
                  backgroundColor: timelapse ? '#fae8ff' : '#ffffff',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: timelapse ? '2px solid #a855f7' : '1px solid #e5e7eb',
                  transition: 'all 0.2s',
                }}>
                  <input
                    type="checkbox"
                    checked={timelapse}
                    onChange={(e) => setTimelapse(e.target.checked)}
                    style={{ width: '18px', height: '18px', accentColor: '#a855f7' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: timelapse ? '#7e22ce' : '#374151' }}>
                      🎬 Timelapse
                    </div>
                    <div style={{ fontSize: '11px', color: timelapse ? '#a855f7' : '#6b7280' }}>
                      Record timelapse video during print
                    </div>
                  </div>
                </label>
              </div>
            </div>

            {/* Printer Selection (if not already selected) */}
            {printers.length > 1 && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', color: '#6b7280', marginBottom: '6px' }}>
                  Select Printer
                </label>
                <select
                  value={selectedUploadPrinter}
                  onChange={(e) => {
                    setSelectedUploadPrinter(e.target.value);
                    loadAmsTrays(e.target.value);
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    fontSize: '14px',
                  }}
                >
                  {printers.map(p => (
                    <option key={p.printerId} value={p.printerId}>
                      {p.printerName}
                    </option>
                  ))}
                </select>
              </div>
            )}
            </>
            )}

            {/* Action Buttons */}
            <div style={{ 
              display: 'flex', 
              gap: '12px',
              paddingTop: '16px',
              borderTop: '1px solid #e5e7eb',
            }}>
              <button
                onClick={handleCancelUpload}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb',
                  backgroundColor: '#ffffff',
                  color: '#374151',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                ❌ Cancel & Delete
              </button>
              <button
                onClick={handleAddToQueue}
                disabled={!selectedUploadPrinter}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: selectedUploadPrinter ? '#3b82f6' : '#9ca3af',
                  color: '#ffffff',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: selectedUploadPrinter ? 'pointer' : 'not-allowed',
                }}
              >
                ✅ Add to Queue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Queue Item Modal */}
      {showEditModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            maxWidth: '500px',
            width: '90%',
            maxHeight: '80vh',
            overflowY: 'auto',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          }}>
            {isLoadingEditDetails ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
                <div>Loading settings...</div>
              </div>
            ) : (
              <>
                {/* Header */}
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  marginBottom: '20px',
                  borderBottom: '1px solid #e5e7eb',
                  paddingBottom: '16px'
                }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '18px', color: '#1f2937' }}>
                      ✏️ Edit Queue Item
                    </h3>
                    <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                      {editingQueueDetails?.job_name}
                    </div>
                  </div>
                  <button
                    onClick={handleCloseEditModal}
                    style={{
                      background: 'none',
                      border: 'none',
                      fontSize: '20px',
                      cursor: 'pointer',
                      color: '#6b7280',
                    }}
                  >
                    ✕
                  </button>
                </div>

                {/* AMS Slot Selection */}
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ fontWeight: 500, color: '#374151', display: 'block', marginBottom: '8px' }}>
                    🎨 Filament Source
                  </label>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                    <button
                      onClick={() => setEditUseAms(true)}
                      style={{
                        flex: 1,
                        padding: '10px',
                        borderRadius: '8px',
                        border: editUseAms ? '2px solid #3b82f6' : '1px solid #d1d5db',
                        backgroundColor: editUseAms ? '#eff6ff' : '#ffffff',
                        cursor: 'pointer',
                      }}
                    >
                      AMS Slot
                    </button>
                    <button
                      onClick={() => { setEditUseAms(false); setEditAmsSlot(255); }}
                      style={{
                        flex: 1,
                        padding: '10px',
                        borderRadius: '8px',
                        border: !editUseAms ? '2px solid #3b82f6' : '1px solid #d1d5db',
                        backgroundColor: !editUseAms ? '#eff6ff' : '#ffffff',
                        cursor: 'pointer',
                      }}
                    >
                      External Spool
                    </button>
                  </div>
                  {editUseAms && (
                    <select
                      value={editAmsSlot}
                      onChange={(e) => setEditAmsSlot(parseInt(e.target.value))}
                      style={{
                        width: '100%',
                        padding: '10px',
                        borderRadius: '8px',
                        border: '1px solid #d1d5db',
                        fontSize: '14px',
                      }}
                    >
                      {amsTrays.map((tray) => (
                        <option key={tray.slot} value={tray.slot}>
                          Slot {tray.slot + 1}: {tray.type || 'Empty'} {tray.brand ? `(${tray.brand})` : ''}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Automation Settings - Simplified (3 checkboxes only) */}
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ fontWeight: 500, color: '#374151', display: 'block', marginBottom: '12px' }}>
                    ⚙️ Print Settings (from Slicer)
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={editAutoBedLeveling} 
                        onChange={(e) => setEditAutoBedLeveling(e.target.checked)} 
                      />
                      <span style={{ fontSize: '13px' }}>🔧 Bed Leveling Calibration</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={editFlowCalibration} 
                        onChange={(e) => setEditFlowCalibration(e.target.checked)} 
                      />
                      <span style={{ fontSize: '13px' }}>💧 Flow Calibration</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={editTimelapse} 
                        onChange={(e) => setEditTimelapse(e.target.checked)} 
                      />
                      <span style={{ fontSize: '13px' }}>📹 Timelapse Recording</span>
                    </label>
                  </div>
                  <div style={{ marginTop: '8px', padding: '8px', backgroundColor: '#fef3c7', borderRadius: '4px', fontSize: '11px', color: '#92400e' }}>
                    ℹ️ All other settings come from your slicer file (.3mf). Files are sent AS-IS without modification.
                  </div>
                </div>

                {/* Download Queue File Button */}
                {editingQueueId && (
                  <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
                    <button
                      onClick={async () => {
                        try {
                          await printFarmClient.downloadQueueFile(editingQueueId);
                          setMessage({ type: 'success', text: '📥 Queue file downloaded' });
                        } catch (err: any) {
                          setMessage({ type: 'error', text: err.message || 'Failed to download queue file' });
                        }
                      }}
                      style={{
                        width: '100%',
                        padding: '10px 16px',
                        borderRadius: '8px',
                        border: '1px solid #10b981',
                        backgroundColor: '#ecfdf5',
                        color: '#059669',
                        fontSize: '13px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                      }}
                    >
                      📥 Download Modified Queue File
                    </button>
                    <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '6px', textAlign: 'center' }}>
                      Download the 3MF file with G-Code modifications applied
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
                  <button
                    onClick={handleCloseEditModal}
                    style={{
                      flex: 1,
                      padding: '12px 20px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      color: '#374151',
                      fontSize: '14px',
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveEditSettings}
                    disabled={isSavingEdit}
                    style={{
                      flex: 1,
                      padding: '12px 20px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: isSavingEdit ? '#9ca3af' : '#3b82f6',
                      color: '#ffffff',
                      fontSize: '14px',
                      fontWeight: 600,
                      cursor: isSavingEdit ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {isSavingEdit ? 'Saving...' : '💾 Save Changes'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

