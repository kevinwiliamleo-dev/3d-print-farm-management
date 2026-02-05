import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { printFarmClient, PrintPreviewResponse, PrintPreviewStep } from '../api/client';

interface PrintPreviewModalProps {
  jobId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
}

// GCode Viewer Types
interface GCodeData {
  job_id: number;
  job_name: string;
  gcode: string[];
  total_lines: number;
  plates: string[];
  selected_plate: string;
}

type LineType = 'comment' | 'move' | 'temp' | 'setting' | 'layer' | 'retract' | 'special' | 'default';

const getLineType = (line: string): LineType => {
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

const getLineColor = (type: LineType): string => {
  switch (type) {
    case 'comment': return 'text-gray-500';
    case 'move': return 'text-blue-600';
    case 'temp': return 'text-orange-600';
    case 'setting': return 'text-purple-600';
    case 'layer': return 'text-green-600 font-bold';
    case 'retract': return 'text-yellow-600';
    case 'special': return 'text-cyan-600';
    default: return 'text-gray-800';
  }
};

const phaseColors: Record<string, string> = {
  preparation: 'bg-blue-100 text-blue-800 border-blue-300',
  calibration: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  printing: 'bg-green-100 text-green-800 border-green-300',
  completion: 'bg-purple-100 text-purple-800 border-purple-300',
};

const phaseLabels: Record<string, string> = {
  preparation: '🔧 Persiapan',
  calibration: '📐 Kalibrasi',
  printing: '🖨️ Cetak',
  completion: '✅ Selesai',
};

export const PrintPreviewModal: React.FC<PrintPreviewModalProps> = ({
  jobId,
  isOpen,
  onClose,
  onConfirm,
}) => {
  const [preview, setPreview] = useState<PrintPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  
  // Tab state
  const [activeTab, setActiveTab] = useState<'job' | 'gcode'>('job');
  
  // GCode viewer state
  const [gcodeData, setGcodeData] = useState<GCodeData | null>(null);
  const [gcodeLoading, setGcodeLoading] = useState(false);
  const [gcodeError, setGcodeError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [highlightSyntax, setHighlightSyntax] = useState(true);
  const [selectedPlate, setSelectedPlate] = useState(1);

  useEffect(() => {
    if (isOpen && jobId) {
      fetchPreview();
      setActiveTab('job');
      setGcodeData(null);
      setGcodeError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, jobId]);

  // Load GCode when switching to gcode tab
  useEffect(() => {
    if (activeTab === 'gcode' && jobId && !gcodeData && !gcodeLoading) {
      loadGCode();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, jobId]);

  const fetchPreview = async () => {
    if (!jobId) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await printFarmClient.getPrintPreview(jobId);
      setPreview(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Gagal memuat preview');
    } finally {
      setLoading(false);
    }
  };

  const loadGCode = async () => {
    if (!jobId) return;
    
    setGcodeLoading(true);
    setGcodeError(null);
    
    try {
      const result = await printFarmClient.getJobGCode(jobId, selectedPlate);
      setGcodeData(result);
    } catch (err: any) {
      setGcodeError(err.response?.data?.detail || 'Gagal memuat G-code');
    } finally {
      setGcodeLoading(false);
    }
  };

  // Filter lines based on search
  const filteredLines = useMemo(() => {
    if (!gcodeData?.gcode) return [];
    if (!searchTerm) return gcodeData.gcode;
    
    const lowerSearch = searchTerm.toLowerCase();
    return gcodeData.gcode.filter(line => 
      line.toLowerCase().includes(lowerSearch)
    );
  }, [gcodeData?.gcode, searchTerm]);

  if (!isOpen) return null;

  const renderStep = (step: PrintPreviewStep) => {
    const isExpanded = expandedStep === step.step;
    
    return (
      <div 
        key={step.step}
        className={`border rounded-lg p-3 mb-2 cursor-pointer transition-all ${
          phaseColors[step.phase] || 'bg-gray-100'
        } ${step.optional ? 'opacity-70' : ''}`}
        onClick={() => setExpandedStep(isExpanded ? null : step.step)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{step.icon}</span>
            <div>
              <div className="font-semibold flex items-center gap-2">
                <span className="bg-white/50 px-2 py-0.5 rounded text-sm">
                  Step {step.step}
                </span>
                {step.action}
                {step.optional && (
                  <span className="text-xs bg-gray-200 px-1.5 py-0.5 rounded">
                    Opsional
                  </span>
                )}
              </div>
              <p className="text-sm opacity-80">{step.description}</p>
            </div>
          </div>
          {step.estimated_time && (
            <span className="text-sm bg-white/50 px-2 py-1 rounded">
              ⏱️ {step.estimated_time}
            </span>
          )}
        </div>
        
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-current/20">
            <p className="text-sm font-medium mb-1">G-code References:</p>
            <div className="flex flex-wrap gap-1">
              {step.gcode_refs.map((ref, idx) => (
                <code key={idx} className="text-xs bg-white/70 px-2 py-0.5 rounded font-mono">
                  {ref}
                </code>
              ))}
            </div>
            {step.details && (
              <div className="mt-2">
                <p className="text-sm font-medium mb-1">Details:</p>
                <pre className="text-xs bg-white/70 p-2 rounded overflow-x-auto">
                  {JSON.stringify(step.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">📋 File Preview</h2>
              {preview && (
                <p className="text-blue-100 text-sm">{preview.job_name}</p>
              )}
            </div>
            <button 
              onClick={onClose}
              className="text-white/80 hover:text-white text-2xl"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b bg-gray-50">
          <button
            onClick={() => setActiveTab('job')}
            className={`flex-1 px-6 py-3 font-medium transition-colors ${
              activeTab === 'job'
                ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
            }`}
          >
            📊 Job Info
          </button>
          <button
            onClick={() => setActiveTab('gcode')}
            className={`flex-1 px-6 py-3 font-medium transition-colors ${
              activeTab === 'gcode'
                ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
            }`}
          >
            📄 G-Code Viewer
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Job Info Tab */}
          {activeTab === 'job' && (
            <>
              {loading && (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
                  <span className="ml-3 text-gray-600">Menganalisis file...</span>
                </div>
              )}

              {error && (
                <div className="bg-red-100 border border-red-300 text-red-700 p-4 rounded-lg">
                  ❌ {error}
                </div>
              )}

              {preview && !loading && (
                <>
                  {/* Summary Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-3 rounded-lg border border-blue-200">
                      <div className="text-blue-600 text-sm">⏱️ Estimasi</div>
                      <div className="font-bold text-lg">{preview.metadata.estimated_time || 'N/A'}</div>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 p-3 rounded-lg border border-green-200">
                      <div className="text-green-600 text-sm">📑 Layer</div>
                      <div className="font-bold text-lg">{preview.metadata.layer_count || 'N/A'}</div>
                    </div>
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-3 rounded-lg border border-orange-200">
                  <div className="text-orange-600 text-sm">🔥 Bed/Nozzle</div>
                  <div className="font-bold text-lg">
                    {preview.metadata.bed_temp || '?'}°/{preview.metadata.nozzle_temp || '?'}°C
                  </div>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-3 rounded-lg border border-purple-200">
                  <div className="text-purple-600 text-sm">🧵 Filamen</div>
                  <div className="font-bold text-lg">
                    {preview.metadata.filament_used_g ? `${preview.metadata.filament_used_g.toFixed(1)}g` : 'N/A'}
                  </div>
                </div>
              </div>

              {/* Automation Detection */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-700 mb-2">🤖 Fitur Otomatis Terdeteksi</h3>
                <div className="flex flex-wrap gap-2">
                  {preview.automation_detected.bed_leveling && (
                    <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm border border-yellow-300">
                      📐 Bed Leveling
                    </span>
                  )}
                  {preview.automation_detected.vibration_calibration && (
                    <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm border border-blue-300">
                      📳 Vibration Test
                    </span>
                  )}
                  {preview.automation_detected.flow_calibration && (
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm border border-green-300">
                      💧 Flow Calibration
                    </span>
                  )}
                  {preview.automation_detected.nozzle_clean && (
                    <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm border border-purple-300">
                      🧹 Nozzle Clean
                    </span>
                  )}
                  {preview.automation_detected.auto_eject && (
                    <span className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm border border-orange-300">
                      📤 Auto Eject
                    </span>
                  )}
                  {!Object.values(preview.automation_detected).some(v => v) && (
                    <span className="text-gray-500 text-sm">Tidak ada fitur otomatis terdeteksi</span>
                  )}
                </div>
              </div>

              {/* Phase Legend */}
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(phaseLabels).map(([phase, label]) => (
                  <span key={phase} className={`px-3 py-1 rounded-full text-xs border ${phaseColors[phase]}`}>
                    {label}
                  </span>
                ))}
              </div>

              {/* Steps */}
              <h3 className="font-semibold text-gray-700 mb-3">
                📝 Langkah-langkah ({preview.total_steps} steps)
              </h3>
              <div className="space-y-2">
                {preview.steps.map(renderStep)}
              </div>
                </>
              )}
            </>
          )}

          {/* GCode Viewer Tab */}
          {activeTab === 'gcode' && (
            <div className="h-full flex flex-col">
              {gcodeLoading && (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
                  <span className="ml-3 text-gray-600">Memuat G-code...</span>
                </div>
              )}

              {gcodeError && (
                <div className="bg-red-100 border border-red-300 text-red-700 p-4 rounded-lg">
                  ❌ {gcodeError}
                  <button
                    onClick={loadGCode}
                    className="ml-4 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                  >
                    Coba Lagi
                  </button>
                </div>
              )}

              {gcodeData && !gcodeLoading && (
                <>
                  {/* GCode Toolbar */}
                  <div className="flex flex-wrap items-center gap-4 mb-4 pb-4 border-b">
                    {/* Plate Selector */}
                    {gcodeData.plates.length > 1 && (
                      <div className="flex items-center gap-2">
                        <label className="text-gray-600 text-sm">Plate:</label>
                        <select
                          value={selectedPlate}
                          onChange={(e) => {
                            setSelectedPlate(Number(e.target.value));
                            setGcodeData(null);
                          }}
                          className="bg-white text-gray-800 text-sm px-3 py-1 rounded border border-gray-300 focus:outline-none focus:border-blue-500"
                        >
                          {gcodeData.plates.map((plate, idx) => (
                            <option key={plate} value={idx + 1}>
                              Plate {idx + 1}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Search */}
                    <div className="flex items-center gap-2 flex-1 max-w-xs">
                      <span className="text-gray-500">🔍</span>
                      <input
                        type="text"
                        placeholder="Cari G-code..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-white text-gray-800 text-sm px-3 py-1 rounded border border-gray-300 focus:outline-none focus:border-blue-500 flex-1"
                      />
                      {searchTerm && (
                        <span className="text-gray-500 text-xs">
                          {filteredLines.length.toLocaleString()} hasil
                        </span>
                      )}
                    </div>

                    {/* Toggle Options */}
                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 text-gray-600 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={showLineNumbers}
                          onChange={(e) => setShowLineNumbers(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        Nomor Baris
                      </label>
                      <label className="flex items-center gap-2 text-gray-600 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={highlightSyntax}
                          onChange={(e) => setHighlightSyntax(e.target.checked)}
                          className="rounded border-gray-300"
                        />
                        Highlight
                      </label>
                    </div>
                  </div>

                  {/* GCode Content */}
                  <div className="flex-1 bg-gray-900 rounded-lg overflow-auto font-mono text-sm p-4 max-h-96">
                    {filteredLines.slice(0, 2000).map((line, idx) => {
                      const actualLineNum = searchTerm 
                        ? gcodeData.gcode.indexOf(line) + 1 
                        : idx + 1;
                      const lineType = getLineType(line);
                      
                      return (
                        <div 
                          key={`${actualLineNum}-${idx}`} 
                          className="flex hover:bg-gray-800 leading-5"
                        >
                          {showLineNumbers && (
                            <span className="text-gray-600 w-14 flex-shrink-0 text-right pr-3 select-none">
                              {actualLineNum}
                            </span>
                          )}
                          <span 
                            className={`flex-1 whitespace-pre ${
                              highlightSyntax ? getLineColor(lineType) : 'text-gray-200'
                            }`}
                          >
                            {line || ' '}
                          </span>
                        </div>
                      );
                    })}
                    {filteredLines.length > 2000 && (
                      <div className="text-center text-gray-500 py-4">
                        ... dan {(filteredLines.length - 2000).toLocaleString()} baris lagi
                      </div>
                    )}
                  </div>

                  {/* GCode Status Bar */}
                  <div className="mt-3 pt-3 border-t text-gray-500 text-sm flex justify-between items-center">
                    <div className="flex gap-4">
                      <span>📋 Total: {gcodeData.total_lines.toLocaleString()} baris</span>
                      <span>📂 {gcodeData.selected_plate}</span>
                    </div>
                    <div className="flex gap-3 text-xs">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                        Move
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                        Temp
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        Layer
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-gray-400"></span>
                        Comment
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Tutup
          </button>
          {onConfirm && (
            <button
              onClick={() => {
                onConfirm();
                onClose();
              }}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              ✅ Mulai Print
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PrintPreviewModal;
