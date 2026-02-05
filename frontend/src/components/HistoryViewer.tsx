import React, { useEffect, useState, useCallback } from 'react';
import { printFarmClient } from '../api/client';

interface HistoryItem {
  history_id: number;
  job_id: number;
  job_name?: string;
  printer_id: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  material_used_grams: number;
  print_success: boolean;
  completion_status: string;
  created_at: string;
}

interface HistoryViewerProps {
  printerId?: string;
}

export const HistoryViewer: React.FC<HistoryViewerProps> = ({ printerId }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all');

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await printFarmClient.getPrintHistory(printerId, 100);
      // Transform to consistent format
      const items = (data || []).map((item: any) => ({
        history_id: item.history_id || item.historyId,
        job_id: item.job_id || item.jobId,
        job_name: item.job_name || item.jobName || `Job #${item.job_id || item.jobId}`,
        printer_id: item.printer_id || item.printerId,
        start_time: item.start_time || item.startTime,
        end_time: item.end_time || item.endTime,
        duration_minutes: item.duration_minutes || item.durationMinutes || 0,
        material_used_grams: item.material_used_grams || item.materialUsedGrams || 0,
        print_success: item.print_success ?? item.printSuccess ?? true,
        completion_status: item.completion_status || item.completionStatus || '',
        created_at: item.created_at || item.createdAt,
      }));
      setHistory(items);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setIsLoading(false);
    }
  }, [printerId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const filteredHistory = history.filter(item => {
    if (filter === 'success') return item.print_success;
    if (filter === 'failed') return !item.print_success;
    return true;
  });

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Calculate stats
  const totalPrints = history.length;
  const successfulPrints = history.filter(h => h.print_success).length;
  const failedPrints = history.filter(h => !h.print_success).length;
  const totalDuration = history.reduce((sum, h) => sum + h.duration_minutes, 0);
  const totalMaterial = history.reduce((sum, h) => sum + h.material_used_grams, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Stats Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
        <div style={{
          padding: '16px',
          backgroundColor: '#ffffff',
          borderRadius: '10px',
          border: '1px solid #e5e7eb',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#1f2937' }}>{totalPrints}</div>
          <div style={{ fontSize: '11px', color: '#6b7280' }}>Total Prints</div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#d1fae5',
          borderRadius: '10px',
          border: '1px solid #6ee7b7',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#047857' }}>{successfulPrints}</div>
          <div style={{ fontSize: '11px', color: '#047857' }}>Successful</div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#fee2e2',
          borderRadius: '10px',
          border: '1px solid #fca5a5',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#b91c1c' }}>{failedPrints}</div>
          <div style={{ fontSize: '11px', color: '#b91c1c' }}>Failed</div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#dbeafe',
          borderRadius: '10px',
          border: '1px solid #93c5fd',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#1d4ed8' }}>
            {formatDuration(totalDuration)}
          </div>
          <div style={{ fontSize: '11px', color: '#1d4ed8' }}>Print Time</div>
        </div>
        
        <div style={{
          padding: '16px',
          backgroundColor: '#fef3c7',
          borderRadius: '10px',
          border: '1px solid #fcd34d',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#b45309' }}>
            {totalMaterial > 1000 ? `${(totalMaterial / 1000).toFixed(1)}kg` : `${Math.round(totalMaterial)}g`}
          </div>
          <div style={{ fontSize: '11px', color: '#b45309' }}>Material Used</div>
        </div>
      </div>

      {/* Filter Buttons */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {(['all', 'success', 'failed'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: filter === f ? 'none' : '1px solid #d1d5db',
              backgroundColor: filter === f ? '#3b82f6' : '#ffffff',
              color: filter === f ? '#ffffff' : '#374151',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {f === 'all' ? 'All' : f === 'success' ? '✓ Success' : '✕ Failed'}
          </button>
        ))}
        
        <button
          onClick={loadHistory}
          disabled={isLoading}
          style={{
            marginLeft: 'auto',
            padding: '8px 16px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            backgroundColor: '#ffffff',
            color: '#374151',
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          ↻ Refresh
        </button>
      </div>

      {/* History Table */}
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e5e7eb',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 120px 100px 80px 80px 100px',
          padding: '12px 16px',
          backgroundColor: '#f9fafb',
          borderBottom: '1px solid #e5e7eb',
          fontSize: '11px',
          fontWeight: 600,
          color: '#6b7280',
          textTransform: 'uppercase',
        }}>
          <div>Job</div>
          <div>Date</div>
          <div>Duration</div>
          <div>Material</div>
          <div>Status</div>
          <div>Result</div>
        </div>

        {/* History Items */}
        {filteredHistory.length === 0 ? (
          <div style={{
            padding: '40px',
            textAlign: 'center',
            color: '#6b7280',
          }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>📜</div>
            <div>No print history yet</div>
          </div>
        ) : (
          filteredHistory.map((item, index) => (
            <div
              key={item.history_id}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 120px 100px 80px 80px 100px',
                padding: '12px 16px',
                borderBottom: index < filteredHistory.length - 1 ? '1px solid #e5e7eb' : 'none',
                alignItems: 'center',
                backgroundColor: !item.print_success ? '#fef2f2' : '#ffffff',
              }}
            >
              {/* Job Info */}
              <div>
                <div style={{ fontWeight: 500, color: '#1f2937', fontSize: '13px' }}>
                  {item.job_name}
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                  Printer: {item.printer_id.slice(0, 10)}...
                </div>
              </div>
              
              {/* Date */}
              <div style={{ fontSize: '12px', color: '#6b7280' }}>
                {formatDate(item.end_time || item.start_time)}
              </div>
              
              {/* Duration */}
              <div style={{ fontSize: '13px', color: '#1f2937', fontWeight: 500 }}>
                {formatDuration(item.duration_minutes)}
              </div>
              
              {/* Material */}
              <div style={{ fontSize: '12px', color: '#6b7280' }}>
                {item.material_used_grams > 0 ? `${Math.round(item.material_used_grams)}g` : '-'}
              </div>
              
              {/* Status Badge */}
              <div>
                <span style={{
                  padding: '3px 8px',
                  borderRadius: '12px',
                  fontSize: '10px',
                  fontWeight: 500,
                  backgroundColor: item.print_success ? '#d1fae5' : '#fee2e2',
                  color: item.print_success ? '#047857' : '#b91c1c',
                }}>
                  {item.print_success ? 'Success' : 'Failed'}
                </span>
              </div>
              
              {/* Completion Status */}
              <div style={{ fontSize: '11px', color: '#6b7280' }}>
                {item.completion_status || '-'}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
