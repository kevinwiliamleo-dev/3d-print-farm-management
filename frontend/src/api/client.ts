/**
 * API Client for 3D Print Farm Management System
 * Follows camelCase naming convention for JavaScript variables
 */

import axios, { AxiosInstance } from 'axios';

interface JobResponse {
  jobId: number;
  jobName: string;
  filename: string;
  uploadTimestamp: string;
  gcodeSizeMb: number;
  loopCount: number;
  currentLoop: number;
  status: string;
  createdAt: string;
  updatedAt: string;
}

interface JobMetadata {
  job_id: number;
  job_name: string;
  filename: string;
  file_size_mb: number;
  file_type: string;
  estimated_time: string | null;
  estimated_time_seconds: number | null;
  filament_used_mm: number | null;
  filament_used_g: number | null;
  filament_type: string | null;
  filament_color: string | null;
  nozzle_temp: number | null;
  bed_temp: number | null;
  layer_count: number | null;
  layer_height: number | null;
  model_name: string | null;
  printer_model: string | null;
  plates?: Array<{
    name: string;
    file: string;
    estimated_time: string | null;
    filament_used_g: number | null;
  }>;
  // Automation settings detected from file
  has_vibration_test?: boolean;
  has_flow_calibration?: boolean;
  has_auto_eject?: boolean;
  has_bed_leveling?: boolean;
  has_clean_nozzle?: boolean;
  has_startup_sound?: boolean;
  has_end_sound?: boolean;
  has_timelapse?: boolean;
}

// GCode Section Interfaces (for structured parsing)
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

interface GCodeModification {
  sectionId: string;
  enabled: boolean;
  startLine: number;
  endLine: number;
}

// Print Preview Interfaces
interface PrintPreviewStep {
  step: number;
  phase: 'preparation' | 'calibration' | 'printing' | 'completion';
  action: string;
  description: string;
  gcode_refs: string[];
  icon: string;
  estimated_time?: string;
  optional?: boolean;
  details?: Record<string, any>;
}

interface PrintPreviewResponse {
  job_id: number;
  job_name: string;
  filename: string;
  metadata: {
    estimated_time: string | null;
    estimated_time_seconds: number | null;
    layer_count: number | null;
    layer_height: number | null;
    filament_used_g: number | null;
    filament_type: string | null;
    bed_temp: number | null;
    nozzle_temp: number | null;
    slicer_name: string | null;
    printer_model: string | null;
  };
  automation_detected: {
    bed_leveling: boolean;
    vibration_calibration: boolean;
    flow_calibration: boolean;
    nozzle_clean: boolean;
    auto_eject: boolean;
  };
  steps: PrintPreviewStep[];
  total_steps: number;
}

interface PrinterResponse {
  printerId: string;
  printerName: string;
  printerStatus: string;
  status?: string;  // Current status: idle, printing, offline
  mqttConnected: boolean;
  printing?: boolean;
  progress?: number;
  autoContinue?: boolean;  // Auto-continue queue after job completion
  // Printer info
  ipAddress?: string;
  model?: string;
  // Time data
  remainingTime?: number;  // seconds remaining
  currentFile?: string;  // currently printing file
  printStartTime?: string;  // ISO timestamp when print started
  // Layer data
  currentLayer?: number;  // current layer number
  totalLayers?: number;  // total layers
  // Temperature data
  nozzleTemp?: number;
  nozzleTargetTemp?: number;
  bedTemp?: number;
  bedTargetTemp?: number;
  chamberTemp?: number;
  // Error tracking
  printError?: number;  // Error code from printer (0 = no error)
  // Print stage tracking
  printStage?: number;  // Current print stage (stg_cur): 1=leveling, 2=heating bed, 7=heating nozzle, 13=homing, 14=cleaning
  createdAt: string;
  updatedAt: string;
}

interface QueueItemResponse {
  queueId: number;
  jobId: number;
  printerId: string;
  positionInQueue: number;
  currentLoop: number;
  loopCount: number;  // Add loop_count from Job table
  queueStatus: string;
  createdAt: string;
}

// ==================== Filament Interfaces ====================

interface FilamentProfile {
  id: number;
  name: string;
  brand: string;
  materialType: string;
  colorHex: string;
  nozzleTempMin: number;
  nozzleTempMax: number;
  nozzleTempDefault: number;
  bedTempMin: number;
  bedTempMax: number;
  bedTempDefault: number;
  maxVolumetricSpeed: number | null;
  kValue: number | null;
  density: number | null;
  diameter: number;
  spoolWeight: number | null;
  dryingTemp: number | null;
  dryingTime: number | null;
  requiresEnclosure: boolean;
  requiresHardenedNozzle: boolean;
  notes: string | null;
  purchaseLink: string | null;
  stockCount: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

interface FilamentProfileCreate {
  name: string;
  brand: string;
  materialType: string;
  colorHex?: string;
  nozzleTempMin?: number;
  nozzleTempMax?: number;
  nozzleTempDefault?: number;
  bedTempMin?: number;
  bedTempMax?: number;
  bedTempDefault?: number;
  maxVolumetricSpeed?: number;
  kValue?: number;
  density?: number;
  diameter?: number;
  spoolWeight?: number;
  dryingTemp?: number;
  dryingTime?: number;
  requiresEnclosure?: boolean;
  requiresHardenedNozzle?: boolean;
  notes?: string;
  purchaseLink?: string;
  stockCount?: number;
}

// ==================== Preset Interfaces ====================

interface PrintPreset {
  preset_id: number;
  name: string;
  description: string | null;
  icon: string;
  color: string;
  is_default: boolean;
  
  // Start GCode (21 templates)
  start_machine: boolean;
  heat_bed_hotend: boolean;
  startup_sound: boolean;
  avoid_end_stop: boolean;
  reset_machine_status: boolean;
  cog_noise_reduction: boolean;
  ams_slot: boolean;
  flow_calibration: boolean;
  vibration_test: boolean;
  wipe_nozzle: boolean;
  clean_nozzle: boolean;
  brush_material_wipe: boolean;
  final_wipe_nozzle: boolean;
  auto_bed_leveling: boolean;
  home_after_wipe: boolean;
  prepare_print: boolean;
  nozzle_load_line: boolean;
  extrude_calibration_test: boolean;
  turn_off_light: boolean;
  final_start: boolean;
  pre_extrude: boolean;
  preheat_offset: number;
  
  // End GCode (6 templates)
  end_print_start: boolean;
  timelapse: boolean;
  move_safe_position: boolean;
  auto_eject: boolean;
  end_sound: boolean;
  end_print_final: boolean;
  cooldown_temp: number;
  
  use_template_mode: boolean;
  
  created_at: string;
  updated_at: string;
}

interface PrintPresetCreate {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  is_default?: boolean;
  
  // Start GCode (21 templates)
  start_machine?: boolean;
  heat_bed_hotend?: boolean;
  startup_sound?: boolean;
  avoid_end_stop?: boolean;
  reset_machine_status?: boolean;
  cog_noise_reduction?: boolean;
  ams_slot?: boolean;
  flow_calibration?: boolean;
  vibration_test?: boolean;
  wipe_nozzle?: boolean;
  clean_nozzle?: boolean;
  brush_material_wipe?: boolean;
  final_wipe_nozzle?: boolean;
  auto_bed_leveling?: boolean;
  home_after_wipe?: boolean;
  prepare_print?: boolean;
  nozzle_load_line?: boolean;
  extrude_calibration_test?: boolean;
  turn_off_light?: boolean;
  final_start?: boolean;
  pre_extrude?: boolean;
  preheat_offset?: number;
  
  // End GCode (6 templates)
  end_print_start?: boolean;
  timelapse?: boolean;
  move_safe_position?: boolean;
  auto_eject?: boolean;
  end_sound?: boolean;
  end_print_final?: boolean;
  cooldown_temp?: number;
  
  use_template_mode?: boolean;
}

class PrintFarmClient {
  private apiClient: AxiosInstance;
  private baseURL: string;

  constructor(baseURL?: string) {
    // Auto-detect backend URL if not provided
    if (!baseURL || baseURL === '') {
      const envUrl = process.env.REACT_APP_BACKEND_URL;
      if (envUrl && envUrl !== '') {
        baseURL = envUrl;
      } else {
        // Auto-detect: Use same hostname as frontend, port 5051
        const protocol = window.location.protocol; // http: or https:
        const hostname = window.location.hostname; // e.g., 192.168.4.197 or localhost
        baseURL = `${protocol}//${hostname}:5051`;
      }
    }
    
    this.baseURL = baseURL;
    this.apiClient = axios.create({
      baseURL: `${baseURL}/api`,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // ==================== Job Endpoints ====================

  async uploadJob(file: File, loopCount: number, onProgress?: (percent: number) => void): Promise<JobResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('loop_count', loopCount.toString());

    const response = await this.apiClient.post('/jobs/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });
    
    // Transform snake_case from backend to camelCase
    const data = response.data;
    return {
      jobId: data.job_id || data.jobId,
      jobName: data.job_name || data.jobName,
      filename: data.filename,
      uploadTimestamp: data.upload_timestamp || data.uploadTimestamp,
      gcodeSizeMb: data.gcode_size_mb || data.gcodeSizeMb,
      loopCount: data.loop_count || data.loopCount,
      currentLoop: data.current_loop || data.currentLoop,
      status: data.status,
      createdAt: data.created_at || data.createdAt,
      updatedAt: data.updated_at || data.updatedAt,
    };
  }

  async getAllJobs(): Promise<JobResponse[]> {
    const response = await this.apiClient.get('/jobs');
    return response.data.jobs.map((job: any) => ({
      jobId: job.job_id,
      jobName: job.job_name,
      filename: job.filename,
      uploadTimestamp: job.upload_timestamp,
      gcodeSizeMb: job.gcode_size_mb,
      loopCount: job.loop_count || 1,
      currentLoop: job.current_loop || 0,
      status: job.status,
      createdAt: job.created_at,
      updatedAt: job.updated_at,
    }));
  }

  async getJobById(jobId: number): Promise<JobResponse> {
    const response = await this.apiClient.get(`/jobs/${jobId}`);
    const job = response.data;
    return {
      jobId: job.job_id,
      jobName: job.job_name,
      filename: job.filename,
      uploadTimestamp: job.upload_timestamp,
      gcodeSizeMb: job.gcode_size_mb,
      loopCount: job.loop_count || 1,
      currentLoop: job.current_loop || 0,
      status: job.status,
      createdAt: job.created_at,
      updatedAt: job.updated_at,
    };
  }

  async getJobMetadata(jobId: number): Promise<JobMetadata> {
    const response = await this.apiClient.get(`/jobs/${jobId}/metadata`);
    return response.data;
  }

  async updateJobLoopCount(jobId: number, loopCount: number): Promise<void> {
    await this.apiClient.patch(`/jobs/${jobId}/loop-count`, null, {
      params: { loop_count: loopCount }
    });
  }

  async getPrintPreview(jobId: number): Promise<PrintPreviewResponse> {
    const response = await this.apiClient.get(`/jobs/${jobId}/print-preview`);
    return response.data;
  }

  // GCode section types
  async getJobGCode(jobId: number, plate: number = 1, maxLines: number = 5000, structured: boolean = true): Promise<{
    job_id: number;
    job_name: string;
    gcode: string[];
    total_lines: number;
    plates: string[];
    selected_plate: string;
    sections?: GCodeSection[];
    printBodyStart?: number;
    endGcodeStart?: number;
  }> {
    const response = await this.apiClient.get(`/jobs/${jobId}/gcode`, {
      params: { plate, max_lines: maxLines, structured }
    });
    return response.data;
  }

  async modifyGCodeSections(jobId: number, modifications: GCodeModification[], plate: number = 1): Promise<{
    success: boolean;
    message: string;
    modified_file?: string;
    changes_applied: number;
    original_file?: string;
  }> {
    const response = await this.apiClient.patch(`/jobs/${jobId}/gcode/sections`, {
      modifications,
      plate
    });
    return response.data;
  }

  getJobThumbnailUrl(jobId: number): string {
    return `${this.baseURL}/api/jobs/${jobId}/thumbnail`;
  }

  async deleteJob(jobId: number): Promise<void> {
    await this.apiClient.delete(`/jobs/${jobId}`);
  }

  // ==================== Printer Endpoints ====================
  // Helper to transform snake_case API response to camelCase
  private transformPrinter(p: any): PrinterResponse {
    return {
      printerId: p.printer_id,
      printerName: p.printer_name,
      printerStatus: p.status || p.printer_status || 'offline',
      status: p.status || 'offline',
      mqttConnected: p.mqtt_connected || false,
      printing: p.printing || false,
      progress: p.progress || 0,
      autoContinue: p.auto_continue !== undefined ? p.auto_continue : true,
      // Printer info
      ipAddress: p.ip_address || '',
      model: p.model || '',
      // Time data
      remainingTime: p.remaining_time || 0,
      currentFile: p.current_file || '',
      // Temperature data
      nozzleTemp: p.nozzle_temp || 0,
      nozzleTargetTemp: p.nozzle_target_temp || 0,
      bedTemp: p.bed_temp || 0,
      bedTargetTemp: p.bed_target_temp || 0,
      chamberTemp: p.chamber_temp || 0,
      createdAt: p.created_at || '',
      updatedAt: p.updated_at || '',
    };
  }

  async registerPrinter(
    printerId: string,
    printerName: string
  ): Promise<PrinterResponse> {
    const response = await this.apiClient.post('/printers', {
      printer_id: printerId,
      printer_name: printerName,
    });
    return this.transformPrinter(response.data);
  }

  async getAllPrinters(): Promise<PrinterResponse[]> {
    const response = await this.apiClient.get('/printers');
    const printers = response.data.printers || [];
    return printers.map((p: any) => this.transformPrinter(p));
  }

  async getPrinterById(printerId: string): Promise<PrinterResponse> {
    const response = await this.apiClient.get(`/printers/${printerId}`);
    return this.transformPrinter(response.data);
  }

  async updatePrinterStatus(
    printerId: string,
    status: string
  ): Promise<PrinterResponse> {
    const response = await this.apiClient.patch(`/printers/${printerId}/status`, {
      printer_status: status,
    });
    return response.data;
  }

  // ==================== AMS Endpoints ====================

  async getAmsTrays(printerId: string): Promise<{
    printer_id: string;
    connected: boolean;
    tray_now: number;
    trays: Array<{
      slot: number;
      name: string;
      type: string;
      color: string;
      remain: number;
      empty: boolean;
      is_external?: boolean;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/printers/${printerId}/ams/trays`);
      return response.data;
    } catch (error) {
      console.error('Failed to get AMS trays:', error);
      return {
        printer_id: printerId,
        connected: false,
        tray_now: 255,
        trays: [],
      };
    }
  }

  async getAmsStatus(printerId: string): Promise<any> {
    try {
      const response = await this.apiClient.get(`/printers/${printerId}/ams`);
      return response.data;
    } catch (error) {
      console.error('Failed to get AMS status:', error);
      return null;
    }
  }

  async amsLoadFilament(printerId: string, slot: number, temperature: number = 220): Promise<{
    success: boolean;
    message: string;
    printer_id: string;
    slot: number;
  }> {
    try {
      const response = await this.apiClient.post(`/printers/${printerId}/ams/load`, {
        slot,
        temperature
      });
      return response.data;
    } catch (error) {
      console.error('Failed to load AMS filament:', error);
      throw error;
    }
  }

  async amsUnloadFilament(printerId: string): Promise<{
    success: boolean;
    message: string;
    printer_id: string;
  }> {
    try {
      const response = await this.apiClient.post(`/printers/${printerId}/ams/unload`);
      return response.data;
    } catch (error) {
      console.error('Failed to unload AMS filament:', error);
      throw error;
    }
  }

  async amsFilamentSettings(printerId: string, slot: number, trayType: string, trayColor: string): Promise<{
    success: boolean;
    message: string;
    printer_id: string;
    slot: number;
  }> {
    try {
      const response = await this.apiClient.post(`/printers/${printerId}/ams/settings`, {
        slot,
        tray_type: trayType,
        tray_color: trayColor
      });
      return response.data;
    } catch (error) {
      console.error('Failed to update AMS filament settings:', error);
      throw error;
    }
  }

  /**
   * Get real-time AMS loading/unloading progress status.
   * Poll this endpoint every 500ms-1s during load/unload operations for smooth progress updates.
   */
  async getAmsLoadingStatus(printerId: string): Promise<{
    success: boolean;
    printer_id: string;
    active: boolean;           // Is load/unload in progress
    is_unload: boolean;        // True if unloading, False if loading
    target_slot: number;       // Target slot for loading (255 = none)
    current_step: number;      // Current step index (0-5 for load, 0-3 for unload)
    step_name: string;         // Human-readable step description
    nozzle_temp: number;       // Current nozzle temperature
    target_temp: number;       // Target nozzle temperature
    completed: boolean;        // True if operation just completed
    total_steps: number;       // Total steps (6 for load, 4 for unload)
    tray_now: number;          // Currently loaded tray (255 = none)
    tray_tar: number;          // Target tray
    hw_switch_state: number;   // Raw hw_switch_state for debugging
    mc_print_sub_stage: number; // Raw mc_print_sub_stage for debugging
    ams_status: number;        // Raw ams_status for debugging
  }> {
    try {
      const response = await this.apiClient.get(`/printers/${printerId}/ams/loading-status`);
      return response.data;
    } catch (error) {
      console.error('Failed to get AMS loading status:', error);
      throw error;
    }
  }

  /**
   * Sync AMS data from printer to database.
   * Inspired by OrcaSlicer's sync mechanism.
   * 
   * Triggers a one-time sync of current AMS slot data from printer to database.
   * Useful after changing filament at the printer or loading/unloading.
   */
  async syncAmsFromPrinter(printerId: string): Promise<{
    success: boolean;
    message: string;
    printer_id: string;
    synced_slots: number;
    timestamp: string;
  }> {
    try {
      const response = await this.apiClient.post(`/printers/${printerId}/ams/sync-from-printer`);
      return response.data;
    } catch (error) {
      console.error('Failed to sync AMS from printer:', error);
      throw error;
    }
  }

  // ==================== AMS Slot Assignment Endpoints ====================

  async getSlotAssignments(printerId: string): Promise<{
    printer_id: string;
    slots: Record<number, {
      slot: number;
      filament_id: number;
      remaining_grams: number;
      updated_at: string;
      name: string;
      brand: string;
      material_type: string;
      color_hex: string;
      color_name: string;
      nozzle_temp_default: number;
      bed_temp_default: number;
      spool_weight: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/filaments/slots/${printerId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get slot assignments:', error);
      throw error;
    }
  }

  async assignFilamentToSlot(printerId: string, slotNumber: number, filamentId: number, remainingGrams?: number): Promise<{
    success: boolean;
    message: string;
    printer_id: string;
    slot: number;
    filament: {
      id: number;
      name: string;
      brand: string;
      material_type: string;
      color_hex: string;
      remaining_grams: number;
    };
  }> {
    try {
      const params = new URLSearchParams();
      params.append('filament_id', filamentId.toString());
      if (remainingGrams !== undefined) {
        params.append('remaining_grams', remainingGrams.toString());
      }
      const response = await this.apiClient.post(`/filaments/slots/${printerId}/${slotNumber}?${params.toString()}`);
      return response.data;
    } catch (error) {
      console.error('Failed to assign filament to slot:', error);
      throw error;
    }
  }

  async updateSlotRemaining(printerId: string, slotNumber: number, remainingGrams: number): Promise<{
    success: boolean;
    printer_id: string;
    slot: number;
    remaining_grams: number;
  }> {
    try {
      const response = await this.apiClient.put(`/filaments/slots/${printerId}/${slotNumber}/remaining?remaining_grams=${remainingGrams}`);
      return response.data;
    } catch (error) {
      console.error('Failed to update slot remaining:', error);
      throw error;
    }
  }

  // ==================== Queue Endpoints ====================

  async addJobToQueue(
    jobId: number, 
    printerId: string,
    settings?: { 
      // AMS settings
      amsSlot: number; 
      amsMapping: string; 
      useAms: boolean;
      filamentAlreadyLoaded?: boolean; // Skip AMS loading if filament already in nozzle
      filamentId?: number;
      // Automation settings (per job)
      skip_preprocessing?: boolean; // Skip all G-code modifications
      autoBedLeveling?: boolean;
      flowCalibration?: boolean;
      timelapse?: boolean;
    }
  ): Promise<QueueItemResponse> {
    const response = await this.apiClient.post('/queue/add', {
      job_id: jobId,
      printer_id: printerId,
      // AMS settings
      ams_slot: settings?.amsSlot ?? 0,
      ams_mapping: settings?.amsMapping ?? '',
      use_ams: settings?.useAms ?? true,
      filament_already_loaded: settings?.filamentAlreadyLoaded ?? false,
      filament_id: settings?.filamentId ?? null,
      // Automation settings
      skip_preprocessing: settings?.skip_preprocessing ?? false,
      auto_bed_leveling: settings?.autoBedLeveling ?? true,
      flow_calibration: settings?.flowCalibration ?? false,
      timelapse: settings?.timelapse ?? false,
    });
    return response.data;
  }

  async getQueueForPrinter(printerId: string): Promise<QueueItemResponse[]> {
    const response = await this.apiClient.get(`/queue/${printerId}`);
    const items = response.data.queue_items || [];
    return items.map((item: any) => ({
      queueId: item.queue_id,
      jobId: item.job_id,
      jobName: item.job_name,
      printerId: item.printer_id,
      positionInQueue: item.position_in_queue,
      currentLoop: item.current_loop || 0,
      loopCount: item.loop_count || 1,
      status: item.status,
      amsSlot: item.ams_slot,
      amsMapping: item.ams_mapping,
      useAms: item.use_ams,
      filamentAlreadyLoaded: item.filament_already_loaded,
      skipPreprocessing: item.skip_preprocessing,
      autoBedLeveling: item.auto_bed_leveling,
      flowCalibration: item.flow_calibration,
      timelapse: item.timelapse,
      createdAt: item.created_at,
      startedAt: item.started_at,
      completedAt: item.completed_at,
      queueFilePath: item.queue_file_path,
    }));
  }

  async removeFromQueue(queueId: number): Promise<void> {
    await this.apiClient.post(`/queue/${queueId}/remove`);
  }

  async getQueueItemDetails(queueId: number): Promise<any> {
    const response = await this.apiClient.get(`/queue/${queueId}/details`);
    return response.data;
  }

  async updateQueueSettings(queueId: number, settings: {
    ams_slot?: number;
    ams_mapping?: string;
    use_ams?: boolean;
    filament_already_loaded?: boolean;
    auto_bed_leveling?: boolean;
    flow_calibration?: boolean;
    timelapse?: boolean;
  }): Promise<void> {
    await this.apiClient.put(`/queue/${queueId}/settings`, settings);
  }

  // Download the modified queue file
  async downloadQueueFile(queueId: number): Promise<void> {
    const response = await this.apiClient.get(`/queue/${queueId}/download`, {
      responseType: 'blob'
    });
    
    // Create download link
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers['content-disposition'];
    let filename = `queue_${queueId}_file.3mf`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, '');
      }
    }
    
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // ==================== Print Control Endpoints ====================

  async startPrint(printerId: string): Promise<any> {
    console.log(`[API] Starting print for printer: ${printerId}`);
    const response = await this.apiClient.post(
      `/print-control/${printerId}/start-print`
    );
    console.log(`[API] Start print response:`, response.data);
    return response.data;
  }

  async pausePrint(printerId: string): Promise<any> {
    console.log(`[API] Pausing print for printer: ${printerId}`);
    const response = await this.apiClient.post(
      `/print-control/${printerId}/pause`
    );
    console.log(`[API] Pause response:`, response.data);
    return response.data;
  }

  async resumePrint(printerId: string): Promise<any> {
    console.log(`[API] Resuming print for printer: ${printerId}`);
    const response = await this.apiClient.post(
      `/print-control/${printerId}/resume`
    );
    console.log(`[API] Resume response:`, response.data);
    return response.data;
  }

  async cancelPrint(printerId: string): Promise<any> {
    console.log(`[API] Cancelling print for printer: ${printerId}`);
    const response = await this.apiClient.post(
      `/print-control/${printerId}/cancel`
    );
    console.log(`[API] Cancel response:`, response.data);
    return response.data;
  }

  async getPrintStatus(printerId: string): Promise<any> {
    const response = await this.apiClient.get(
      `/print-control/${printerId}/status`
    );
    return response.data;
  }

  async getMqttStatus(printerId: string): Promise<any> {
    const response = await this.apiClient.get(
      `/print-control/${printerId}/mqtt-status`
    );
    return response.data;
  }

  // ==================== Printer Discovery Endpoints ====================

  async discoverPrintersOnNetwork(): Promise<PrinterResponse[]> {
    const response = await this.apiClient.post('/printers/discover/scan');
    return response.data.printers || [];
  }

  async discoverByIp(ipAddress: string): Promise<any> {
    const response = await this.apiClient.post('/printers/discover/by-ip', {
      ip_address: ipAddress
    });
    return response.data;
  }

  async getDiscoveryStatus(): Promise<any> {
    const response = await this.apiClient.get('/printers/discover/status');
    return response.data;
  }

  async startAsyncDiscovery(): Promise<any> {
    const response = await this.apiClient.get('/printers/discover/async');
    return response.data;
  }

  async getDiscoveryResults(): Promise<any> {
    const response = await this.apiClient.get('/printers/discover/results');
    return response.data;
  }

  async lookupPrinterById(printerId: string): Promise<any> {
    const response = await this.apiClient.post(`/printers/lookup-by-id/${printerId}`);
    return response.data;
  }

  async refreshPrinterStatus(printerId: string): Promise<any> {
    const response = await this.apiClient.post(`/printers/${printerId}/refresh`);
    return response.data;
  }

  async deletePrinter(printerId: string): Promise<void> {
    await this.apiClient.delete(`/printers/${printerId}`);
  }

  // ==================== History Endpoints ====================

  async getPrintHistory(printerId?: string, limit: number = 50): Promise<any[]> {
    const params = printerId ? `?printer_id=${printerId}&limit=${limit}` : `?limit=${limit}`;
    const response = await this.apiClient.get(`/history${params}`);
    return response.data.history || [];
  }

  async getHistoryStats(): Promise<any> {
    const response = await this.apiClient.get('/history/stats');
    return response.data;
  }

  // ==================== Queue Status Endpoints ====================

  async getQueueStatus(printerId: string): Promise<any> {
    const response = await this.apiClient.get(`/queue/${printerId}/status`);
    return response.data;
  }

  async updateQueuePosition(queueId: number, newPosition: number): Promise<any> {
    const response = await this.apiClient.put(`/queue/${queueId}/position`, {
      new_position: newPosition
    });
    return response.data;
  }

  async startNextJob(printerId: string): Promise<any> {
    const response = await this.apiClient.post(`/print-control/${printerId}/start-print`);
    return response.data;
  }

  // ==================== Filament Endpoints ====================

  // Transform snake_case from API to camelCase
  private transformFilament(f: any): FilamentProfile {
    return {
      id: f.filament_id || f.id,
      name: f.name,
      brand: f.brand,
      materialType: f.material_type,
      colorHex: f.color_hex,
      nozzleTempMin: f.nozzle_temp_min,
      nozzleTempMax: f.nozzle_temp_max,
      nozzleTempDefault: f.nozzle_temp_default,
      bedTempMin: f.bed_temp_min,
      bedTempMax: f.bed_temp_max,
      bedTempDefault: f.bed_temp_default,
      maxVolumetricSpeed: f.max_volumetric_speed,
      kValue: f.k_value,
      density: f.density,
      diameter: f.diameter,
      spoolWeight: f.spool_weight,
      dryingTemp: f.drying_temp,
      dryingTime: f.drying_time,
      requiresEnclosure: f.requires_enclosure,
      requiresHardenedNozzle: f.requires_hardened_nozzle,
      notes: f.notes,
      purchaseLink: f.purchase_link,
      stockCount: f.stock_count,
      isActive: f.is_active,
      createdAt: f.created_at,
      updatedAt: f.updated_at,
    };
  }

  // Transform camelCase to snake_case for API
  private filamentToApi(f: FilamentProfileCreate): any {
    return {
      name: f.name,
      brand: f.brand,
      material_type: f.materialType,
      color_hex: f.colorHex,
      nozzle_temp_min: f.nozzleTempMin,
      nozzle_temp_max: f.nozzleTempMax,
      nozzle_temp_default: f.nozzleTempDefault,
      bed_temp_min: f.bedTempMin,
      bed_temp_max: f.bedTempMax,
      bed_temp_default: f.bedTempDefault,
      max_volumetric_speed: f.maxVolumetricSpeed,
      k_value: f.kValue,
      density: f.density,
      diameter: f.diameter,
      spool_weight: f.spoolWeight,
      drying_temp: f.dryingTemp,
      drying_time: f.dryingTime,
      requires_enclosure: f.requiresEnclosure,
      requires_hardened_nozzle: f.requiresHardenedNozzle,
      notes: f.notes,
      purchase_link: f.purchaseLink,
      stock_count: f.stockCount,
    };
  }

  async getAllFilaments(): Promise<FilamentProfile[]> {
    const response = await this.apiClient.get('/filaments');
    // Handle both array response and object with filaments property
    const filaments = Array.isArray(response.data) ? response.data : (response.data.filaments || response.data || []);
    return filaments.map((f: any) => this.transformFilament(f));
  }

  async getFilamentById(id: number): Promise<FilamentProfile> {
    const response = await this.apiClient.get(`/filaments/${id}`);
    return this.transformFilament(response.data);
  }

  async createFilament(filament: FilamentProfileCreate): Promise<FilamentProfile> {
    const response = await this.apiClient.post('/filaments', this.filamentToApi(filament));
    return this.transformFilament(response.data);
  }

  async updateFilament(id: number, filament: FilamentProfileCreate): Promise<FilamentProfile> {
    const response = await this.apiClient.put(`/filaments/${id}`, this.filamentToApi(filament));
    return this.transformFilament(response.data);
  }

  async deleteFilament(id: number): Promise<void> {
    await this.apiClient.delete(`/filaments/${id}`);
  }

  async getFilamentMaterials(): Promise<string[]> {
    const response = await this.apiClient.get('/filaments/materials');
    return response.data.materials || [];
  }

  async getFilamentBrands(): Promise<string[]> {
    const response = await this.apiClient.get('/filaments/brands');
    return response.data.brands || [];
  }

  async addFilamentStock(id: number, grams: number = 1000): Promise<FilamentProfile> {
    const response = await this.apiClient.post(`/filaments/${id}/stock/add`, { grams });
    return this.transformFilament(response.data);
  }

  async useFilamentStock(id: number, grams: number = 0): Promise<FilamentProfile> {
    const response = await this.apiClient.post(`/filaments/${id}/stock/use`, { grams });
    return this.transformFilament(response.data);
  }

  // ==================== Bucket List Endpoints ====================

  async getBucketList(printerId: string): Promise<any[]> {
    const response = await this.apiClient.get(`/bucket-list/${printerId}`);
    return response.data.bucket_items || [];
  }

  async moveQueueToBucket(queueId: number): Promise<any> {
    const response = await this.apiClient.post(`/bucket-list/from-queue/${queueId}`);
    return response.data;
  }

  async moveBucketToQueue(bucketId: number, printerId?: string): Promise<any> {
    const response = await this.apiClient.post(`/bucket-list/${bucketId}/to-queue`, {
      printer_id: printerId
    });
    return response.data;
  }

  async removeFromBucket(bucketId: number, deleteFile: boolean = false): Promise<any> {
    const response = await this.apiClient.delete(`/bucket-list/${bucketId}`, {
      params: { delete_file: deleteFile }
    });
    return response.data;
  }

  async updateBucketNotes(bucketId: number, notes: string): Promise<any> {
    const response = await this.apiClient.put(`/bucket-list/${bucketId}/notes`, null, {
      params: { notes }
    });
    return response.data;
  }

  // ==================== Preset Endpoints ====================

  async getPresets(): Promise<PrintPreset[]> {
    const response = await this.apiClient.get('/presets');
    return response.data;
  }

  async getDefaultPreset(): Promise<PrintPreset | null> {
    const response = await this.apiClient.get('/presets/default');
    return response.data;
  }

  async getPresetById(presetId: number): Promise<PrintPreset> {
    const response = await this.apiClient.get(`/presets/${presetId}`);
    return response.data;
  }

  async createPreset(preset: PrintPresetCreate): Promise<PrintPreset> {
    const response = await this.apiClient.post('/presets', preset);
    return response.data;
  }

  async updatePreset(presetId: number, preset: Partial<PrintPresetCreate>): Promise<PrintPreset> {
    const response = await this.apiClient.put(`/presets/${presetId}`, preset);
    return response.data;
  }

  async deletePreset(presetId: number): Promise<void> {
    await this.apiClient.delete(`/presets/${presetId}`);
  }

  async setDefaultPreset(presetId: number): Promise<void> {
    await this.apiClient.post(`/presets/${presetId}/set-default`);
  }

  async createDefaultPresets(): Promise<{ success: boolean; message: string; created: number }> {
    const response = await this.apiClient.post('/presets/create-defaults');
    return response.data;
  }
}

export const printFarmClient = new PrintFarmClient();
export type { 
  JobResponse, 
  JobMetadata, 
  PrinterResponse, 
  QueueItemResponse, 
  FilamentProfile, 
  FilamentProfileCreate,
  PrintPreviewStep,
  PrintPreviewResponse,
  PrintPreset,
  PrintPresetCreate
};
