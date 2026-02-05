import React, { useState, useEffect } from 'react';

interface PrinterFile {
  name: string;
  size: number;
  size_mb: number;
  is_3mf: boolean;
  is_gcode: boolean;
  modified?: string;
  path?: string;  // "root" or "cache"
  full_path?: string;  // Full path like "cache/file.3mf"
}

interface PrinterFilesTabProps {
  printerStatus?: string;
}

export const PrinterFilesTab: React.FC<PrinterFilesTabProps> = ({ printerStatus = 'offline' }) => {
  const [files, setFiles] = useState<PrinterFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(true); // Start collapsed to save space

  // Load files from printer SD card
  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:5000/api/printer-files/list');
      const data = await response.json();
      
      if (data.files) {
        setFiles(data.files);
      }
    } catch (err) {
      setError(`Failed to load files: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Print file from SD card
  const printFile = async (filename: string, fullPath?: string) => {
    const fileToUse = fullPath || filename;
    
    if (!fileToUse) {
      setError('No file selected');
      return;
    }

    try {
      const response = await fetch(`http://localhost:5000/api/printer-files/print/${encodeURIComponent(fileToUse)}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        setError(null);
      } else {
        setError(data.detail || 'Failed to start print');
      }
    } catch (err) {
      setError(`Error: ${err}`);
    }
  };

  // Delete file from SD card
  const deleteFile = async (filename: string, fullPath?: string) => {
    const fileToDelete = fullPath || filename;
    
    try {
      console.log(`🗑️ Deleting file: ${fileToDelete}`);
      const response = await fetch(`http://localhost:5000/api/printer-files/${encodeURIComponent(fileToDelete)}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      console.log('Delete response:', data);
      
      if (response.ok) {
        setError(null);
        setConfirmDelete(null);
        // Show success message with location info
        const location = data.location || (fileToDelete.includes('/') ? 'cache' : 'root');
        const locationLabel = location === 'cache' ? '📂 cache/' : '📁 root/';
        const successMsg = `🗑️ Successfully deleted: ${locationLabel}${filename}`;
        console.log(successMsg);
        // Show temporary success indicator
        setError(null);
        setTimeout(() => {
          loadFiles(); // Refresh list after 1 second
        }, 1000);
      } else {
        const errorMsg = data.detail || data.message || 'Failed to delete file';
        console.error('Delete error:', errorMsg);
        setError(errorMsg);
        setConfirmDelete(null);
      }
    } catch (err: any) {
      const errorMsg = `Error deleting file: ${err.message || err}`;
      console.error(errorMsg);
      setError(errorMsg);
      setConfirmDelete(null);
    }
  };

  // Load files only when user expands the collapsible (lazy loading)
  // This prevents slow tab loading due to FTPS connection
  useEffect(() => {
    if (!isCollapsed && files.length === 0 && !loading) {
      loadFiles();
    }
  }, [isCollapsed]);

  const totalSize = files.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024);

  return (
    <div style={{
      backgroundColor: '#ffffff',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      padding: '16px 20px',
    }}>
      {/* Collapsible Header */}
      <div 
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ 
            display: 'inline-block', 
            transition: 'transform 0.2s',
            transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)'
          }}>
            ▼
          </span>
          📁 SD Card Files
        </h3>
        {!isCollapsed && (
          <button
            onClick={(e) => { e.stopPropagation(); loadFiles(); }}
            disabled={loading}
            style={{
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 500,
              color: '#ffffff',
              backgroundColor: loading ? '#9ca3af' : '#2563eb',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '⏳ Loading...' : '🔄 Refresh'}
          </button>
        )}
      </div>

      {/* Collapsible Content */}
      {!isCollapsed && (
        <div style={{ marginTop: '16px' }}>

      {/* Error Message */}
      {error && (
        <div style={{
          marginBottom: '12px',
          padding: '12px',
          backgroundColor: '#fee2e2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          color: '#dc2626',
          fontSize: '14px',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* File List or Empty State */}
      {files.length === 0 ? (
        <div style={{
          padding: '24px',
          textAlign: 'center',
          backgroundColor: '#f9fafb',
          borderRadius: '8px',
          color: '#6b7280',
          fontSize: '14px',
        }}>
          {loading ? '⏳ Loading files...' : '📭 No files found on SD card'}
        </div>
      ) : (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '8px',
          maxHeight: '500px',
          overflowY: 'auto',
          paddingRight: '4px'
        }}>
          {files.map((file) => (
            <div
              key={file.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px',
                backgroundColor: '#f9fafb',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
              }}
            >
              {/* File Name and Info */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                <span style={{ fontSize: '20px' }}>
                  {file.is_3mf ? '📦' : file.is_gcode ? '⚙️' : '📄'}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 500, color: '#1f2937', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {file.path === 'cache' && <span style={{ color: '#f59e0b', marginRight: '8px' }}>📂 cache/</span>}
                    {file.size_mb > 0 ? `${file.size_mb.toFixed(1)} MB` : `${file.size} B`}
                  </div>
                </div>
              </div>

              {/* Type Badge */}
              <div style={{ marginLeft: '12px' }}>
                {file.is_3mf ? (
                  <span style={{
                    display: 'inline-block',
                    padding: '4px 10px',
                    backgroundColor: '#dbeafe',
                    color: '#1d4ed8',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}>
                    3MF
                  </span>
                ) : file.is_gcode ? (
                  <span style={{
                    display: 'inline-block',
                    padding: '4px 10px',
                    backgroundColor: '#dcfce7',
                    color: '#166534',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}>
                    G-CODE
                  </span>
                ) : (
                  <span style={{
                    display: 'inline-block',
                    padding: '4px 10px',
                    backgroundColor: '#f3f4f6',
                    color: '#6b7280',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}>
                    OTHER
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', marginLeft: '12px' }}>
                <button
                  onClick={() => printFile(file.name, file.full_path)}
                  disabled={printerStatus === 'offline'}
                  style={{
                    padding: '8px 14px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: '#ffffff',
                    backgroundColor: printerStatus === 'offline' ? '#9ca3af' : '#10b981',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: printerStatus === 'offline' ? 'not-allowed' : 'pointer',
                  }}
                  title="Print this file"
                >
                  ▶️ Print
                </button>
                <button
                  onClick={() => setConfirmDelete(file.full_path || file.name)}
                  style={{
                    padding: '8px 14px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: '#ffffff',
                    backgroundColor: '#ef4444',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
                  title="Delete this file"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats Footer */}
      {files.length > 0 && (
        <div style={{
          marginTop: '12px',
          paddingTop: '12px',
          borderTop: '1px solid #e5e7eb',
          fontSize: '13px',
          color: '#6b7280',
        }}>
          📊 {files.length} file{files.length !== 1 ? 's' : ''} • 💾 {totalSize.toFixed(1)} MB total
        </div>
      )}

        </div>
      )}

      {/* Confirmation Dialog */}
      {confirmDelete && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #e5e7eb',
            padding: '24px',
            maxWidth: '400px',
            margin: '0 16px',
            boxShadow: '0 10px 15px rgba(0, 0, 0, 0.1)',
          }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
              Delete File?
            </h3>
            <p style={{ margin: '0 0 20px 0', fontSize: '14px', color: '#6b7280' }}>
              Are you sure you want to delete <strong style={{ color: '#1f2937' }}>{confirmDelete}</strong>?
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setConfirmDelete(null)}
                style={{
                  padding: '10px 20px',
                  fontSize: '14px',
                  fontWeight: 500,
                  color: '#1f2937',
                  backgroundColor: '#e5e7eb',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => deleteFile(confirmDelete)}
                style={{
                  padding: '10px 20px',
                  fontSize: '14px',
                  fontWeight: 500,
                  color: '#ffffff',
                  backgroundColor: '#dc2626',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrinterFilesTab;
