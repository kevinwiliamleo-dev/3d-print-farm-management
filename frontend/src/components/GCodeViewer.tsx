import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { printFarmClient } from '../api/client';

interface GCodeViewerProps {
  jobId: number;
  isOpen: boolean;
  onClose: () => void;
}

interface GCodeData {
  job_id: number;
  job_name: string;
  gcode: string[];
  total_lines: number;
  plates: string[];
  selected_plate: string;
}

// Line type classification for syntax highlighting
type LineType = 'comment' | 'move' | 'temp' | 'setting' | 'layer' | 'retract' | 'special' | 'default';

const getLineType = (line: string): LineType => {
  const trimmed = line.trim();
  if (trimmed.startsWith(';')) return 'comment';
  if (trimmed.startsWith('G0 ') || trimmed.startsWith('G1 ')) return 'move';
  if (trimmed.match(/^M10[49]/)) return 'temp'; // M104, M109 nozzle temp
  if (trimmed.match(/^M14[01]/)) return 'temp'; // M140, M141 bed temp
  if (trimmed.match(/^M190/)) return 'temp'; // M190 wait for bed
  if (trimmed.match(/^;LAYER:/i)) return 'layer';
  if (trimmed.match(/^G10|^G11/)) return 'retract';
  if (trimmed.match(/^M[0-9]+/)) return 'setting';
  if (trimmed.match(/^G[0-9]+/)) return 'special';
  return 'default';
};

const getLineColor = (type: LineType): string => {
  switch (type) {
    case 'comment': return 'text-gray-400';
    case 'move': return 'text-blue-400';
    case 'temp': return 'text-orange-400';
    case 'setting': return 'text-purple-400';
    case 'layer': return 'text-green-400 font-bold';
    case 'retract': return 'text-yellow-400';
    case 'special': return 'text-cyan-400';
    default: return 'text-gray-200';
  }
};

export const GCodeViewer: React.FC<GCodeViewerProps> = ({ jobId, isOpen, onClose }) => {
  const [data, setData] = useState<GCodeData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlate, setSelectedPlate] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [highlightSyntax, setHighlightSyntax] = useState(true);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 500 });

  const loadGCode = useCallback(async () => {
    if (!jobId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await printFarmClient.getJobGCode(jobId, selectedPlate);
      setData(result);
      setVisibleRange({ start: 0, end: Math.min(500, result.gcode.length) });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load G-code');
    } finally {
      setIsLoading(false);
    }
  }, [jobId, selectedPlate]);

  useEffect(() => {
    if (isOpen && jobId) {
      loadGCode();
    }
  }, [isOpen, jobId, loadGCode]);

  // Filter lines based on search
  const filteredLines = useMemo(() => {
    if (!data?.gcode) return [];
    if (!searchTerm) return data.gcode;
    
    const lowerSearch = searchTerm.toLowerCase();
    return data.gcode.filter(line => 
      line.toLowerCase().includes(lowerSearch)
    );
  }, [data?.gcode, searchTerm]);

  // Virtual scrolling - only render visible lines
  const visibleLines = useMemo(() => {
    return filteredLines.slice(visibleRange.start, visibleRange.end);
  }, [filteredLines, visibleRange]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, clientHeight, scrollHeight } = e.currentTarget;
    const lineHeight = 20; // Approximate line height in pixels
    const totalLines = filteredLines.length;
    
    const startLine = Math.floor(scrollTop / lineHeight);
    const visibleCount = Math.ceil(clientHeight / lineHeight) + 50; // Buffer
    
    setVisibleRange({
      start: Math.max(0, startLine - 25),
      end: Math.min(totalLines, startLine + visibleCount + 25)
    });
  };

  const handleLoadMore = () => {
    if (data) {
      const currentMax = visibleRange.end;
      setVisibleRange({
        start: 0,
        end: Math.min(data.gcode.length, currentMax + 1000)
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg w-11/12 max-w-6xl h-5/6 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="bg-gray-800 px-6 py-4 rounded-t-lg flex items-center justify-between border-b border-gray-700">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="text-2xl">📄</span>
              G-Code Viewer
            </h2>
            {data && (
              <span className="text-gray-400 text-sm">
                {data.job_name} • {data.total_lines.toLocaleString()} lines
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl font-bold w-8 h-8 flex items-center justify-center rounded hover:bg-gray-700"
          >
            ×
          </button>
        </div>

        {/* Toolbar */}
        <div className="bg-gray-800 px-6 py-3 flex items-center gap-4 border-b border-gray-700 flex-wrap">
          {/* Plate Selector */}
          {data && data.plates.length > 1 && (
            <div className="flex items-center gap-2">
              <label className="text-gray-400 text-sm">Plate:</label>
              <select
                value={selectedPlate}
                onChange={(e) => setSelectedPlate(Number(e.target.value))}
                className="bg-gray-700 text-white text-sm px-3 py-1 rounded border border-gray-600 focus:outline-none focus:border-blue-500"
              >
                {data.plates.map((plate, idx) => (
                  <option key={plate} value={idx + 1}>
                    Plate {idx + 1}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Search */}
          <div className="flex items-center gap-2 flex-1 max-w-md">
            <span className="text-gray-400">🔍</span>
            <input
              type="text"
              placeholder="Search G-code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-gray-700 text-white text-sm px-3 py-1 rounded border border-gray-600 focus:outline-none focus:border-blue-500 flex-1"
            />
            {searchTerm && (
              <span className="text-gray-400 text-xs">
                {filteredLines.length.toLocaleString()} matches
              </span>
            )}
          </div>

          {/* Toggle Options */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={showLineNumbers}
                onChange={(e) => setShowLineNumbers(e.target.checked)}
                className="rounded bg-gray-700 border-gray-600"
              />
              Line Numbers
            </label>
            <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={highlightSyntax}
                onChange={(e) => setHighlightSyntax(e.target.checked)}
                className="rounded bg-gray-700 border-gray-600"
              />
              Syntax Highlight
            </label>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading G-code...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-red-400">
                <span className="text-4xl mb-4 block">⚠️</span>
                <p>{error}</p>
                <button
                  onClick={loadGCode}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : data ? (
            <>
              <div 
                className="flex-1 overflow-auto font-mono text-sm bg-gray-900 p-4"
                onScroll={handleScroll}
              >
                {/* Virtual scroll padding for lines before */}
                {visibleRange.start > 0 && (
                  <div style={{ height: visibleRange.start * 20 }} />
                )}
                
                {visibleLines.map((line, idx) => {
                  const actualLineNum = searchTerm 
                    ? data.gcode.indexOf(line) + 1 
                    : visibleRange.start + idx + 1;
                  const lineType = getLineType(line);
                  
                  return (
                    <div 
                      key={`${actualLineNum}-${idx}`} 
                      className="flex hover:bg-gray-800 leading-5"
                    >
                      {showLineNumbers && (
                        <span className="text-gray-600 w-16 flex-shrink-0 text-right pr-4 select-none">
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
                
                {/* Virtual scroll padding for lines after */}
                {visibleRange.end < filteredLines.length && (
                  <div style={{ height: (filteredLines.length - visibleRange.end) * 20 }} />
                )}
              </div>

              {/* Status Bar */}
              <div className="bg-gray-800 px-6 py-2 text-gray-400 text-sm flex justify-between items-center border-t border-gray-700">
                <div className="flex gap-6">
                  <span>📋 Total: {data.total_lines.toLocaleString()} lines</span>
                  <span>📂 {data.selected_plate}</span>
                </div>
                <div className="flex gap-4">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-blue-400"></span>
                    Moves
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-orange-400"></span>
                    Temperature
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-green-400"></span>
                    Layer
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-gray-400"></span>
                    Comments
                  </span>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default GCodeViewer;
