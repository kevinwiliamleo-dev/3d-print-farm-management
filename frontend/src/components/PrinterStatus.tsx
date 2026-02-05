import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PrinterResponse, printFarmClient } from '../api/client';
import { AmsStatusDisplay } from './AmsStatusDisplay';
import { getPrintStageText, shouldShowPrintStage } from '../utils/printStage';

interface PrinterStatusProps {
  printer: PrinterResponse | null;
  cameraSource?: 'bambu' | 'custom';
  customCameraUrl?: string;
}

export const PrinterStatus: React.FC<PrinterStatusProps> = ({ 
  printer,
  cameraSource = 'bambu',
  customCameraUrl = ''
}) => {
  const [cameraLive, setCameraLive] = useState(false);
  const [cameraError, setCameraError] = useState(false);
  const [useStream, setUseStream] = useState(true); // Start with MJPEG stream, fallback to snapshot
  const [imageKey, setImageKey] = useState(0); // Force image refresh
  const [isPaused, setIsPaused] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const mountedRef = useRef(true);

  // Sync isPaused state with printer status from WebSocket
  useEffect(() => {
    if (printer) {
      const printerStatus = printer.status || 'offline';
      setIsPaused(printerStatus === 'paused');
    }
  }, [printer?.status]);

  // Handle pause/resume
  const handlePauseResume = async () => {
    if (!printer) return;
    const action = isPaused ? 'resume' : 'pause';
    console.log(`[PrinterStatus] ${action.toUpperCase()} button clicked for printer: ${printer.printerId}`);
    setActionLoading(action);
    try {
      if (isPaused) {
        console.log(`[PrinterStatus] Sending RESUME command to printer: ${printer.printerId}`);
        const result = await printFarmClient.resumePrint(printer.printerId);
        console.log(`[PrinterStatus] RESUME response:`, result);
        setIsPaused(false);
      } else {
        console.log(`[PrinterStatus] Sending PAUSE command to printer: ${printer.printerId}`);
        const result = await printFarmClient.pausePrint(printer.printerId);
        console.log(`[PrinterStatus] PAUSE response:`, result);
        setIsPaused(true);
      }
    } catch (error) {
      console.error(`[PrinterStatus] Error ${action}:`, error);
    } finally {
      setActionLoading(null);
    }
  };

  // Format remaining time from seconds to readable string
  const formatRemainingTime = (seconds: number): string => {
    if (!seconds || seconds <= 0) return '--:--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
  };

  // Handle stop/cancel
  const handleStop = async () => {
    if (!printer) return;
    console.log(`[PrinterStatus] STOP button clicked for printer: ${printer.printerId}`);
    if (!window.confirm('Are you sure you want to stop the print? This cannot be undone.')) {
      console.log(`[PrinterStatus] STOP cancelled by user`);
      return;
    }
    setActionLoading('stop');
    try {
      console.log(`[PrinterStatus] Sending CANCEL command to printer: ${printer.printerId}`);
      const result = await printFarmClient.cancelPrint(printer.printerId);
      console.log(`[PrinterStatus] CANCEL response:`, result);
    } catch (error) {
      console.error(`[PrinterStatus] Error stopping print:`, error);
    } finally {
      setActionLoading(null);
    }
  };

  // Camera URLs based on source setting
  const bambuStreamUrl = 'http://localhost:5000/api/camera/stream';
  const bambuSnapshotUrl = () => `http://localhost:5000/api/camera/snapshot?t=${Date.now()}`;
  
  // Determine which URL to use
  const getStreamUrl = () => cameraSource === 'custom' && customCameraUrl ? customCameraUrl : bambuStreamUrl;
  const getSnapshotUrl = () => cameraSource === 'custom' && customCameraUrl ? customCameraUrl : bambuSnapshotUrl();

  // Handle stream/image events
  const handleImageLoad = useCallback(() => {
    if (mountedRef.current) {
      setCameraLive(true);
      setCameraError(false);
    }
  }, []);

  const handleImageError = useCallback(() => {
    if (mountedRef.current) {
      setCameraError(true);
      setCameraLive(false);
      // If stream fails, try snapshot mode as fallback
      if (useStream) {
        console.log('MJPEG stream failed, falling back to snapshot mode');
        setUseStream(false);
      }
    }
  }, [useStream]);

  // Snapshot polling mode - works reliably
  useEffect(() => {
    mountedRef.current = true;
    
    if (!useStream && printer) {
      // Polling mode - reliable camera updates
      const refreshSnapshot = () => {
        if (imgRef.current && mountedRef.current) {
          const newSrc = getSnapshotUrl();
          const preloadImg = new Image();
          preloadImg.onload = () => {
            if (mountedRef.current && imgRef.current) {
              imgRef.current.src = newSrc;
              setCameraLive(true);
              setCameraError(false);
            }
          };
          preloadImg.onerror = () => {
            if (mountedRef.current) {
              setCameraError(true);
              setCameraLive(false);
            }
          };
          preloadImg.src = newSrc;
        }
      };
      
      refreshSnapshot();
      // 1000ms interval = 1 FPS - balanced between smoothness and performance
      // FDM Monster uses event-driven updates, we use polling as fallback
      const intervalId = setInterval(refreshSnapshot, 1000);
      
      return () => {
        mountedRef.current = false;
        clearInterval(intervalId);
      };
    }
    
    return () => {
      mountedRef.current = false;
    };
  }, [useStream]);

  if (!printer) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '300px',
        backgroundColor: '#f9fafb',
        borderRadius: '12px',
        border: '2px dashed #e5e7eb',
      }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🖨️</div>
        <div style={{ fontSize: '16px', color: '#6b7280', fontWeight: 500 }}>
          Select a printer to view details
        </div>
      </div>
    );
  }

  const status = printer.status || 'offline';
  const progress = printer.progress || 0;
  const mqttConnected = printer.mqttConnected ?? false;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Status Card - Always visible */}
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        padding: '24px',
      }}>
        {/* Header with Status */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
              🖨️ Printer Status
            </span>
            <span style={{
              padding: '4px 10px',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: status === 'printing' ? '#fef3c7' : status === 'paused' ? '#dbeafe' : '#f3f4f6',
              color: status === 'printing' ? '#92400e' : status === 'paused' ? '#1e40af' : '#6b7280',
            }}>
              {status === 'printing' ? '▶️ Printing' : status === 'paused' ? '⏸️ Paused' : '⏹️ Idle'}
            </span>
            {/* Print Stage - show detailed stage during printing */}
            {status === 'printing' && shouldShowPrintStage(printer?.printStage) && (
              <span style={{
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '11px',
                fontWeight: 500,
                backgroundColor: '#eff6ff',
                color: '#1e40af',
              }}>
                {getPrintStageText(printer.printStage!)}
              </span>
            )}
          </div>
          {(status === 'printing' || status === 'paused') && (
            <span style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b' }}>
              {progress}%
            </span>
          )}
        </div>
        
        {/* Progress Bar - only show when printing or paused */}
        {(status === 'printing' || status === 'paused') && (
          <div style={{ 
            height: '12px', 
            backgroundColor: '#f3f4f6', 
            borderRadius: '6px',
            overflow: 'hidden',
            marginBottom: '16px',
          }}>
            <div style={{ 
              height: '100%', 
              width: `${progress}%`,
              backgroundColor: isPaused || status === 'paused' ? '#3b82f6' : '#f59e0b',
              borderRadius: '6px',
              transition: 'width 0.5s ease',
            }} />
          </div>
        )}
          
        {/* Status Cards Grid - Always visible */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
          marginBottom: '16px',
        }}>
          {/* Remaining Time Card */}
          <div style={{
            padding: '16px',
              backgroundColor: (status === 'printing' || status === 'paused') ? '#f0fdf4' : '#f9fafb',
              borderRadius: '12px',
              textAlign: 'center',
              border: `1px solid ${(status === 'printing' || status === 'paused') ? '#bbf7d0' : '#e5e7eb'}`,
            }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>⏱️</div>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px', fontWeight: 500 }}>
                Remaining
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: (status === 'printing' || status === 'paused') ? '#166534' : '#9ca3af' }}>
                {(status === 'printing' || status === 'paused') ? formatRemainingTime(printer?.remainingTime || 0) : '-'}
              </div>
            </div>

            {/* Layer Card */}
            <div style={{
              padding: '16px',
              backgroundColor: (status === 'printing' || status === 'paused') ? '#eff6ff' : '#f9fafb',
              borderRadius: '12px',
              textAlign: 'center',
              border: `1px solid ${(status === 'printing' || status === 'paused') ? '#bfdbfe' : '#e5e7eb'}`,
            }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>📐</div>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px', fontWeight: 500 }}>
                Layer
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: (status === 'printing' || status === 'paused') ? '#1e40af' : '#9ca3af' }}>
                {(status === 'printing' || status === 'paused') ? `${printer?.currentLayer || 0} / ${printer?.totalLayers || 0}` : '-'}
              </div>
            </div>

            {/* Nozzle Temp Card */}
            <div style={{
              padding: '16px',
              backgroundColor: (printer?.nozzleTemp || 0) > 50 ? '#fef2f2' : '#f9fafb',
              borderRadius: '12px',
              textAlign: 'center',
              border: `1px solid ${(printer?.nozzleTemp || 0) > 50 ? '#fecaca' : '#e5e7eb'}`,
            }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>🔥</div>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px', fontWeight: 500 }}>
                Nozzle
              </div>
              <div style={{ 
                fontSize: '18px', 
                fontWeight: 700, 
                color: (printer?.nozzleTemp || 0) > 50 ? '#dc2626' : '#1f2937',
              }}>
                {(printer?.nozzleTemp || 0).toFixed(0)}°C
                {(printer?.nozzleTargetTemp || 0) > 0 && (
                  <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 400 }}>
                    {' → '}{(printer?.nozzleTargetTemp || 0).toFixed(0)}°C
                  </span>
                )}
              </div>
            </div>

            {/* Bed Temp Card */}
            <div style={{
              padding: '16px',
              backgroundColor: (printer?.bedTemp || 0) > 40 ? '#fffbeb' : '#f9fafb',
              borderRadius: '12px',
              textAlign: 'center',
              border: `1px solid ${(printer?.bedTemp || 0) > 40 ? '#fde68a' : '#e5e7eb'}`,
            }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>🛏️</div>
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px', fontWeight: 500 }}>
                Bed
              </div>
              <div style={{ 
                fontSize: '18px', 
                fontWeight: 700, 
                color: (printer?.bedTemp || 0) > 40 ? '#d97706' : '#1f2937',
              }}>
                {(printer?.bedTemp || 0).toFixed(0)}°C
                {(printer?.bedTargetTemp || 0) > 0 && (
                  <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 400 }}>
                    {' → '}{(printer?.bedTargetTemp || 0).toFixed(0)}°C
                  </span>
                )}
              </div>
            </div>
          </div>

        {/* Current File - only show when printing */}
        {(status === 'printing' || status === 'paused') && printer?.currentFile && (
          <div style={{
            padding: '8px 12px',
            backgroundColor: '#f9fafb',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#6b7280',
            marginBottom: '8px',
          }}>
            📄 {printer.currentFile}
          </div>
        )}

        {/* Control Buttons - only show when printing or paused */}
        {(status === 'printing' || status === 'paused') && (
          <div style={{ 
            display: 'flex', 
            gap: '12px', 
            marginTop: '12px',
            paddingTop: '16px',
            borderTop: '1px solid #e5e7eb',
          }}>
            {/* Pause/Resume Button */}
            <button
              onClick={handlePauseResume}
              disabled={actionLoading !== null}
              style={{
                flex: 1,
                padding: '12px 20px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: isPaused || status === 'paused' ? '#10b981' : '#3b82f6',
                color: '#ffffff',
                fontSize: '14px',
                fontWeight: 600,
                cursor: actionLoading ? 'wait' : 'pointer',
                opacity: actionLoading ? 0.7 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              {actionLoading === 'pause' || actionLoading === 'resume' ? (
                '⏳ Processing...'
              ) : isPaused || status === 'paused' ? (
                <>▶️ Resume Print</>
              ) : (
                <>⏸️ Pause Print</>
              )}
            </button>
            
            {/* Stop Button */}
            <button
              onClick={handleStop}
              disabled={actionLoading !== null}
              style={{
                flex: 1,
                padding: '12px 20px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                fontSize: '14px',
                fontWeight: 600,
                cursor: actionLoading ? 'wait' : 'pointer',
                opacity: actionLoading ? 0.7 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              {actionLoading === 'stop' ? '⏳ Stopping...' : '⏹️ Stop Print'}
            </button>
          </div>
        )}
      </div>

      {/* 1. Camera Feed */}
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        overflow: 'hidden',
      }}>
        {/* Camera Header */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#1f2937' }}>
              📷 Camera Feed
            </h3>
            {/* Live Status Indicator */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '12px',
              backgroundColor: cameraLive ? '#dcfce7' : cameraError ? '#fee2e2' : '#f3f4f6',
              fontSize: '11px',
              fontWeight: 500,
              color: cameraLive ? '#166534' : cameraError ? '#991b1b' : '#6b7280',
            }}>
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: cameraLive ? '#22c55e' : cameraError ? '#ef4444' : '#9ca3af',
                animation: cameraLive ? 'pulse 2s infinite' : 'none',
              }}></span>
              {cameraLive ? 'LIVE' : cameraError ? 'Offline' : 'Connecting...'}
            </div>
          </div>
          {/* Camera Source Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '12px',
            backgroundColor: cameraSource === 'bambu' ? '#dbeafe' : '#fef3c7',
            fontSize: '11px',
            fontWeight: 500,
            color: cameraSource === 'bambu' ? '#1e40af' : '#92400e',
          }}>
            {cameraSource === 'bambu' ? '🏭 Bambu Camera' : '🌐 Custom URL'}
          </div>
        </div>
        <div style={{ 
          backgroundColor: '#1f2937',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '600px',
          position: 'relative',
        }}>
          {cameraError && !cameraLive && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#9ca3af',
              zIndex: 1,
            }}>
              <div style={{ fontSize: '40px', marginBottom: '12px' }}>📷</div>
              <div style={{ fontSize: '14px' }}>Camera unavailable</div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                {cameraSource === 'bambu' 
                  ? 'Bambu Camera - Retrying...' 
                  : customCameraUrl 
                    ? `Custom URL: ${customCameraUrl.substring(0, 30)}...` 
                    : 'No custom URL configured'}
              </div>
              {cameraSource === 'custom' && !customCameraUrl && (
                <div style={{ 
                  fontSize: '11px', 
                  marginTop: '12px', 
                  color: '#f59e0b',
                  padding: '8px 16px',
                  backgroundColor: 'rgba(245, 158, 11, 0.1)',
                  borderRadius: '6px',
                }}>
                  ⚠️ Set camera URL in Settings tab
                </div>
              )}
            </div>
          )}
          <img 
            ref={imgRef}
            src={useStream ? getStreamUrl() : getSnapshotUrl()}
            alt="Printer Camera"
            onLoad={handleImageLoad}
            onError={handleImageError}
            style={{
              width: '100%',
              height: '600px',
              objectFit: 'contain',
              borderRadius: '4px',
              opacity: cameraLive ? 1 : 0.3,
              transition: 'opacity 0.3s ease',
              backgroundColor: '#1f2937',
            }}
          />
        </div>
      </div>

      {/* 2. AMS Status Display */}
      <AmsStatusDisplay printerId={printer.printerId} />
    </div>
  );
};

// Add keyframes for pulse animation
const style = document.createElement('style');
style.textContent = `
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;
if (!document.querySelector('style[data-camera-pulse]')) {
  style.setAttribute('data-camera-pulse', 'true');
  document.head.appendChild(style);
}
