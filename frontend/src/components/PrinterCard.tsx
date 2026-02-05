import React, { useState } from 'react';
import { printFarmClient, PrinterResponse } from '../api/client';
import axios from 'axios';

interface PrinterCardProps {
  printer: PrinterResponse;
  isSelected: boolean;
  onSelect: () => void;
  onRefresh: () => void;
  onDelete: () => void;
  onJobAdded?: () => void;
}

export const PrinterCard: React.FC<PrinterCardProps> = ({
  printer,
  isSelected,
  onSelect,
  onRefresh,
  onDelete,
  onJobAdded,
}) => {
  const [liveStatus, setLiveStatus] = useState<any>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTogglingAutoContinue, setIsTogglingAutoContinue] = useState(false);

  const handleToggleAutoContinue = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsTogglingAutoContinue(true);
    try {
      const newValue = !printer.autoContinue;
      const response = await axios.patch(`http://localhost:5000/api/printers/${printer.printerId}/auto-continue?auto_continue=${newValue}`);
      
      // Update parent component's printer state without full refresh
      // This preserves MQTT data (progress, temperature, etc.)
      if (response.data) {
        // Just trigger a minimal refresh or update local state
        // The parent will re-render with updated autoContinue value
        onRefresh();
      }
    } catch (err) {
      console.error('Toggle auto-continue failed:', err);
    } finally {
      setIsTogglingAutoContinue(false);
    }
  };

  const handleConnect = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsConnecting(true);
    try {
      // Call reconnect API to force MQTT reconnection
      await axios.post(`http://localhost:5000/api/printers/${printer.printerId}/reconnect`);
      // Also refresh status
      const result = await printFarmClient.refreshPrinterStatus(printer.printerId);
      setLiveStatus(result);
      onRefresh();
    } catch (err) {
      console.error('Connect failed:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Remove "${printer.printerName}"?`)) {
      try {
        await printFarmClient.deletePrinter(printer.printerId);
        onDelete();
      } catch (err) {
        console.error('Delete failed:', err);
      }
    }
  };

  // Drag & Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    const validFile = files.find(f => 
      f.name.toLowerCase().endsWith('.3mf') || f.name.toLowerCase().endsWith('.stl')
    );

    if (!validFile) {
      setUploadMessage({ type: 'error', text: 'Please drop a .3mf or .stl file' });
      setTimeout(() => setUploadMessage(null), 3000);
      return;
    }

    setIsUploading(true);
    try {
      const job = await printFarmClient.uploadJob(validFile, 1);
      await printFarmClient.addJobToQueue(job.jobId, printer.printerId);
      setUploadMessage({ type: 'success', text: `Added: ${job.jobName}` });
      onJobAdded?.();
    } catch (err: any) {
      let errorText = 'Upload failed';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        errorText = typeof detail === 'string' ? detail : (detail.msg || 'Upload failed');
      } else if (err.message) {
        errorText = err.message;
      }
      setUploadMessage({ type: 'error', text: errorText });
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadMessage(null), 3000);
    }
  };

  const status = liveStatus?.status || printer.status || 'offline';
  const progress = liveStatus?.progress || printer.progress || 0;
  const mqttConnected = liveStatus?.mqtt_connected ?? printer.mqttConnected ?? false;
  const reconnecting = liveStatus?.reconnecting ?? (printer as any).reconnecting ?? false;

  const getStatusColor = () => {
    switch (status) {
      case 'printing': return 'bg-amber-500';
      case 'idle': return 'bg-emerald-500';
      case 'paused': return 'bg-blue-500';
      default: return 'bg-gray-400';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'printing': return 'Printing';
      case 'idle': return 'Ready';
      case 'paused': return 'Paused';
      default: return 'Offline';
    }
  };

  // Printer image - local SVG
  const printerImage = '/printer-icon.svg';

  return (
    <div
      onClick={onSelect}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        backgroundColor: isDragOver ? '#dbeafe' : isSelected ? '#f8fafc' : '#ffffff',
        border: isDragOver ? '2px dashed #3b82f6' : isSelected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
        borderRadius: '12px',
        padding: '16px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        position: 'relative',
      }}
    >
      {/* Upload Overlay */}
      {isDragOver && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
        }}>
          <div style={{
            padding: '12px 24px',
            backgroundColor: '#3b82f6',
            color: '#ffffff',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: 600,
          }}>
            📤 Drop to add to queue
          </div>
        </div>
      )}

      {/* Uploading Indicator */}
      {isUploading && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
        }}>
          <div style={{ fontSize: '14px', color: '#3b82f6' }}>⏳ Uploading...</div>
        </div>
      )}

      {/* Upload Message */}
      {uploadMessage && (
        <div style={{
          position: 'absolute',
          top: '8px',
          left: '8px',
          right: '8px',
          padding: '8px 12px',
          backgroundColor: uploadMessage.type === 'success' ? '#d1fae5' : '#fee2e2',
          color: uploadMessage.type === 'success' ? '#047857' : '#b91c1c',
          borderRadius: '6px',
          fontSize: '12px',
          zIndex: 10,
        }}>
          {uploadMessage.text}
        </div>
      )}

      {/* Header Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        {/* Printer Image */}
        <div style={{
          width: '48px',
          height: '48px',
          borderRadius: '8px',
          backgroundColor: '#f3f4f6',
          overflow: 'hidden',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}>
          <img 
            src={printerImage}
            alt="Bambu Lab"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
          {/* Status indicator overlay */}
          <div
            className={getStatusColor()}
            style={{
              position: 'absolute',
              bottom: '2px',
              right: '2px',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              border: '2px solid white',
            }}
          />
        </div>
        
        {/* Printer Name */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span style={{ 
              fontWeight: 600, 
              fontSize: '15px', 
              color: '#1f2937',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {printer.printerName || 'Unnamed Printer'}
            </span>
            {/* Connect Button - Show when MQTT disconnected */}
            {!mqttConnected && !reconnecting && (
              <button
                onClick={handleConnect}
                disabled={isConnecting}
                style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: '#10b981',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 500,
                  cursor: isConnecting ? 'wait' : 'pointer',
                  opacity: isConnecting ? 0.6 : 1,
                  whiteSpace: 'nowrap',
                }}
              >
                {isConnecting ? '...' : 'Connect'}
              </button>
            )}
          </div>
          <div style={{ 
            fontSize: '12px', 
            color: '#9ca3af',
            fontFamily: 'monospace',
          }}>
            {printer.printerId?.slice(0, 12)}...
          </div>
        </div>

        {/* Status Badge */}
        <div style={{
          padding: '4px 10px',
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: 500,
          backgroundColor: status === 'printing' ? '#fef3c7' : status === 'idle' ? '#d1fae5' : '#f3f4f6',
          color: status === 'printing' ? '#b45309' : status === 'idle' ? '#047857' : '#6b7280',
        }}>
          {getStatusText()}
        </div>
      </div>

      {/* Progress Bar - Only when printing */}
      {status === 'printing' && progress > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '12px', color: '#6b7280' }}>Progress</span>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#f59e0b' }}>{progress}%</span>
          </div>
          <div style={{ 
            height: '6px', 
            backgroundColor: '#e5e7eb', 
            borderRadius: '3px',
            overflow: 'hidden',
          }}>
            <div style={{ 
              height: '100%', 
              width: `${progress}%`,
              backgroundColor: '#f59e0b',
              borderRadius: '3px',
              transition: 'width 0.5s ease',
            }} />
          </div>
        </div>
      )}

      {/* Connection & Actions Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        {/* MQTT Status */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '6px',
          fontSize: '12px',
          color: mqttConnected ? '#059669' : reconnecting ? '#d97706' : '#dc2626',
        }}>
          <div style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: mqttConnected ? '#10b981' : reconnecting ? '#f59e0b' : '#ef4444',
          }} />
          {mqttConnected ? 'Connected' : reconnecting ? 'Reconnecting...' : 'Disconnected'}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleDelete}
            style={{
              padding: '6px 10px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: '#fef2f2',
              color: '#dc2626',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Auto Continue Toggle */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        backgroundColor: '#f9fafb',
        borderRadius: '8px',
        marginTop: '8px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: 500 }}>
            Auto Continue
          </span>
          <span style={{ fontSize: '11px', color: '#9ca3af' }}>
            {printer.autoContinue ? 'Queue will auto-start' : 'Manual start required'}
          </span>
        </div>
        <button
          onClick={handleToggleAutoContinue}
          disabled={isTogglingAutoContinue}
          style={{
            padding: '4px 8px',
            borderRadius: '12px',
            border: 'none',
            backgroundColor: printer.autoContinue ? '#10b981' : '#d1d5db',
            color: '#ffffff',
            fontSize: '11px',
            fontWeight: 600,
            cursor: isTogglingAutoContinue ? 'wait' : 'pointer',
            opacity: isTogglingAutoContinue ? 0.6 : 1,
            minWidth: '45px',
            transition: 'all 0.2s ease',
          }}
        >
          {isTogglingAutoContinue ? '...' : printer.autoContinue ? 'ON' : 'OFF'}
        </button>
      </div>
    </div>
  );
};
