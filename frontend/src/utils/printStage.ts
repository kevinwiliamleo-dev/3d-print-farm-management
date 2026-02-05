/**
 * Print stage mapping from Bambu Lab printer
 * stg_cur values from MQTT messages
 */
export const getPrintStageText = (stageCode: number): string => {
  const stages: Record<number, string> = {
    '-2': '⏳ Preparing',  // Custom: PREPARE gcode_state
    '-1': '',  // Idle
    0: '',  // Printing (normal)
    1: '🔧 Auto Bed Leveling',
    2: '🔥 Heating Bed',
    3: '🔄 Sweeping XY',
    4: '🎞️ Changing Filament',
    5: '⏸️ M400 Pause',
    6: '⚠️ Filament Runout',
    7: '🔥 Heating Nozzle',
    8: '🔬 Calibrating Extrusion',
    9: '📡 Scanning Bed',
    10: '👁️ Inspecting First Layer',
    11: '🔍 Identifying Build Plate',
    12: '📐 Calibrating Lidar',
    13: '🏠 Homing Tool Head',
    14: '🧹 Cleaning Nozzle',
    15: '🌡️ Checking Temperature',
    16: '⏸️ Paused by User',
  };

  return stages[stageCode] || '';
};

/**
 * Check if stage text should be displayed (only show specific stages)
 */
export const shouldShowPrintStage = (stageCode: number | null | undefined): boolean => {
  // Don't show if null, undefined, 0 (normal printing), -1 (idle), or 255 (offline/invalid)
  if (stageCode === null || stageCode === undefined || stageCode === 0 || stageCode === -1 || stageCode === 255) {
    return false;
  }
  // Show preparing state (-2) and all valid stages (1-16)
  return (stageCode === -2) || (stageCode >= 1 && stageCode <= 16);
};
