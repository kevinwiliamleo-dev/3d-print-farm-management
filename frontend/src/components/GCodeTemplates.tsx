import React, { useState, useEffect } from 'react';
import { printFarmClient, PrintPreset, PrintPresetCreate } from '../api/client';

interface Template {
  template_key: string;
  template_id: number;
  name: string;
  description: string;
  enabled: boolean;
  order: number;
  category: string;
  gcode: string;
  controllable?: boolean;
  setting_key?: string;
  printer_model?: string;
}

interface Variable {
  name: string;
  description: string;
}

interface TemplatesData {
  start_templates: Template[];
  end_templates: Template[];
  variables: Variable[];
}

type TabType = 'templates' | 'presets';

export const GCodeTemplates: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('templates');
  const [templates, setTemplates] = useState<TemplatesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [previewGcode, setPreviewGcode] = useState<{ start: string; end: string } | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [reordering, setReordering] = useState(false);
  
  // Presets state
  const [presets, setPresets] = useState<PrintPreset[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);
  const [editingPreset, setEditingPreset] = useState<PrintPreset | null>(null);
  const [showPresetForm, setShowPresetForm] = useState(false);
  const [presetFormData, setPresetFormData] = useState<PrintPresetCreate>({
    name: '',
    description: '',
    icon: '⚡',
    color: '#3b82f6',
    is_default: false,
    
    // Start GCode (21 templates) - all default false, user can enable
    start_machine: false,
    heat_bed_hotend: false,
    startup_sound: false,
    avoid_end_stop: false,
    reset_machine_status: false,
    cog_noise_reduction: false,
    ams_slot: false,
    flow_calibration: false,
    vibration_test: false,
    wipe_nozzle: false,
    clean_nozzle: false,
    brush_material_wipe: false,
    final_wipe_nozzle: false,
    auto_bed_leveling: false,
    home_after_wipe: false,
    prepare_print: false,
    nozzle_load_line: false,
    extrude_calibration_test: false,
    turn_off_light: false,
    final_start: false,
    pre_extrude: false,
    preheat_offset: 20,
    
    // End GCode (6 templates) - all default false
    end_print_start: false,
    timelapse: false,
    move_safe_position: false,
    auto_eject: false,
    end_sound: false,
    end_print_final: false,
    cooldown_temp: 32,
  });
  
  // Preview settings
  const [previewSettings, setPreviewSettings] = useState({
    nozzle_temp: 220,
    bed_temp: 55,
    filament_type: 'PLA',
    ams_slot: 0,
    preheat_offset: 20,
    pre_extrude_length: 2.2,
    cooldown_temp: 32,
    filament_already_loaded: false,
  });

  useEffect(() => {
    loadTemplates();
    loadPresets();
  }, []);

  // Presets management functions
  const loadPresets = async () => {
    try {
      setPresetsLoading(true);
      const data = await printFarmClient.getPresets();
      // Do not auto-recreate defaults after user deletes them; just show empty state
      setPresets(data);
    } catch (err) {
      console.error('Failed to load presets:', err);
    } finally {
      setPresetsLoading(false);
    }
  };

  const handleSavePreset = async () => {
    try {
      setSaving(true);
      if (editingPreset) {
        await printFarmClient.updatePreset(editingPreset.preset_id, presetFormData);
        setMessage({ type: 'success', text: 'Preset updated!' });
      } else {
        await printFarmClient.createPreset(presetFormData);
        setMessage({ type: 'success', text: 'Preset created!' });
      }
      await loadPresets();
      setShowPresetForm(false);
      setEditingPreset(null);
      resetPresetForm();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to save preset' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePreset = async (preset: PrintPreset) => {
    if (!window.confirm(`Delete preset "${preset.name}"?`)) return;
    try {
      await printFarmClient.deletePreset(preset.preset_id);
      setMessage({ type: 'success', text: 'Preset deleted!' });
      await loadPresets();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to delete preset' });
    }
  };

  const handleSetDefault = async (preset: PrintPreset) => {
    try {
      await printFarmClient.setDefaultPreset(preset.preset_id);
      setMessage({ type: 'success', text: `"${preset.name}" is now the default preset` });
      await loadPresets();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to set default' });
    }
  };

  const handleEditPreset = (preset: PrintPreset) => {
    setEditingPreset(preset);
    setPresetFormData({
      name: preset.name,
      description: preset.description || '',
      icon: preset.icon,
      color: preset.color,
      is_default: preset.is_default,
      
      // Start GCode (21 templates)
      start_machine: preset.start_machine ?? false,
      heat_bed_hotend: preset.heat_bed_hotend ?? false,
      startup_sound: preset.startup_sound ?? false,
      avoid_end_stop: preset.avoid_end_stop ?? false,
      reset_machine_status: preset.reset_machine_status ?? false,
      cog_noise_reduction: preset.cog_noise_reduction ?? false,
      ams_slot: preset.ams_slot ?? false,
      flow_calibration: preset.flow_calibration ?? false,
      vibration_test: preset.vibration_test ?? false,
      wipe_nozzle: preset.wipe_nozzle ?? false,
      clean_nozzle: preset.clean_nozzle ?? false,
      brush_material_wipe: preset.brush_material_wipe ?? false,
      final_wipe_nozzle: preset.final_wipe_nozzle ?? false,
      auto_bed_leveling: preset.auto_bed_leveling ?? false,
      home_after_wipe: preset.home_after_wipe ?? false,
      prepare_print: preset.prepare_print ?? false,
      nozzle_load_line: preset.nozzle_load_line ?? false,
      extrude_calibration_test: preset.extrude_calibration_test ?? false,
      turn_off_light: preset.turn_off_light ?? false,
      final_start: preset.final_start ?? false,
      pre_extrude: preset.pre_extrude ?? false,
      preheat_offset: preset.preheat_offset ?? 20,
      
      // End GCode (6 templates)
      end_print_start: preset.end_print_start ?? false,
      timelapse: preset.timelapse ?? false,
      move_safe_position: preset.move_safe_position ?? false,
      auto_eject: preset.auto_eject ?? false,
      end_sound: preset.end_sound ?? false,
      end_print_final: preset.end_print_final ?? false,
      cooldown_temp: preset.cooldown_temp ?? 32,
    });
    setShowPresetForm(true);
  };

  const resetPresetForm = () => {
    setPresetFormData({
      name: '',
      description: '',
      icon: '⚡',
      color: '#3b82f6',
      is_default: false,
      
      // Start GCode (21 templates) - all default false
      start_machine: false,
      heat_bed_hotend: false,
      startup_sound: false,
      avoid_end_stop: false,
      reset_machine_status: false,
      cog_noise_reduction: false,
      ams_slot: false,
      flow_calibration: false,
      vibration_test: false,
      wipe_nozzle: false,
      clean_nozzle: false,
      brush_material_wipe: false,
      final_wipe_nozzle: false,
      auto_bed_leveling: false,
      home_after_wipe: false,
      prepare_print: false,
      nozzle_load_line: false,
      extrude_calibration_test: false,
      turn_off_light: false,
      final_start: false,
      pre_extrude: false,
      preheat_offset: 20,
      
      // End GCode (6 templates) - all default false
      end_print_start: false,
      timelapse: false,
      move_safe_position: false,
      auto_eject: false,
      end_sound: false,
      end_print_final: false,
      cooldown_temp: 32,
    });
  };

  const handleNewPreset = () => {
    setEditingPreset(null);
    resetPresetForm();
    setShowPresetForm(true);
  };

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5000/api/templates');
      if (!response.ok) throw new Error('Failed to load templates');
      const data = await response.json();
      setTemplates(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const updateTemplate = async (templateId: string, updates: Partial<Template>) => {
    try {
      setSaving(true);
      const response = await fetch(`http://localhost:5000/api/templates/${templateId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update template');
      
      setMessage({ type: 'success', text: 'Template saved!' });
      setTimeout(() => setMessage(null), 3000);
      
      // Reload templates
      await loadTemplates();
      setEditingTemplate(null);
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  // Move template up or down
  const moveTemplate = async (templateId: string, direction: 'up' | 'down', category: 'start' | 'end') => {
    if (!templates) return;
    
    const templateList = category === 'start' ? templates.start_templates : templates.end_templates;
    const currentIndex = templateList.findIndex(t => t.template_key === templateId);
    
    if (currentIndex === -1) return;
    if (direction === 'up' && currentIndex === 0) return;
    if (direction === 'down' && currentIndex === templateList.length - 1) return;
    
    const swapIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    const currentTemplate = templateList[currentIndex];
    const swapTemplate = templateList[swapIndex];
    
    try {
      setReordering(true);
      
      // Swap orders
      const currentOrder = currentTemplate.order;
      const swapOrder = swapTemplate.order;
      
      await Promise.all([
        fetch(`http://localhost:5000/api/templates/${currentTemplate.template_key}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order: swapOrder }),
        }),
        fetch(`http://localhost:5000/api/templates/${swapTemplate.template_key}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order: currentOrder }),
        }),
      ]);
      
      await loadTemplates();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to reorder templates' });
    } finally {
      setReordering(false);
    }
  };

  const generatePreview = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/templates/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(previewSettings),
      });
      if (!response.ok) throw new Error('Failed to generate preview');
      const data = await response.json();
      setPreviewGcode({ start: data.start_gcode, end: data.end_gcode });
      setShowPreview(true);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to generate preview' });
    }
  };

  const resetTemplates = async () => {
    if (!window.confirm('Reset all templates to defaults? This cannot be undone.')) return;
    
    try {
      const response = await fetch('http://localhost:5000/api/templates/reset', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to reset templates');
      setMessage({ type: 'success', text: 'Templates reset to defaults!' });
      await loadTemplates();
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to reset templates' });
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#6b7280' }}>
        <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
        Loading templates...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: '#dc2626', backgroundColor: '#fef2f2', borderRadius: '8px' }}>
        <strong>Error:</strong> {error}
        <button 
          onClick={loadTemplates}
          style={{ marginLeft: '10px', padding: '4px 12px', cursor: 'pointer' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px' }}>
      {/* Tab Navigation */}
      <div style={{ 
        display: 'flex', 
        gap: '4px',
        marginBottom: '20px',
        borderBottom: '2px solid #e5e7eb',
        paddingBottom: '0',
      }}>
        <button
          onClick={() => setActiveTab('templates')}
          style={{
            padding: '12px 24px',
            backgroundColor: activeTab === 'templates' ? '#ffffff' : 'transparent',
            border: 'none',
            borderBottom: activeTab === 'templates' ? '3px solid #3b82f6' : '3px solid transparent',
            color: activeTab === 'templates' ? '#3b82f6' : '#6b7280',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            marginBottom: '-2px',
          }}
        >
          📝 GCode Templates
        </button>
        <button
          onClick={() => setActiveTab('presets')}
          style={{
            padding: '12px 24px',
            backgroundColor: activeTab === 'presets' ? '#ffffff' : 'transparent',
            border: 'none',
            borderBottom: activeTab === 'presets' ? '3px solid #3b82f6' : '3px solid transparent',
            color: activeTab === 'presets' ? '#3b82f6' : '#6b7280',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            marginBottom: '-2px',
          }}
        >
          ⚙️ Print Presets
        </button>
      </div>

      {/* Message */}
      {message && (
        <div style={{
          padding: '10px 16px',
          marginBottom: '16px',
          borderRadius: '6px',
          backgroundColor: message.type === 'success' ? '#ecfdf5' : '#fef2f2',
          color: message.type === 'success' ? '#059669' : '#dc2626',
          fontSize: '13px',
        }}>
          {message.type === 'success' ? '✅' : '❌'} {message.text}
        </div>
      )}

      {/* Templates Tab Content */}
      {activeTab === 'templates' && (
        <>
          {/* Header */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '20px',
            paddingBottom: '16px',
            borderBottom: '1px solid #e5e7eb'
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', color: '#1f2937' }}>📝 GCode Templates</h2>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#6b7280' }}>
                Edit templates yang digunakan untuk generate start/end gcode
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={generatePreview}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                👁️ Preview
              </button>
              <button
                onClick={resetTemplates}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                🔄 Reset to Defaults
              </button>
            </div>
          </div>

      {/* Variables Reference */}
      <div style={{
        backgroundColor: '#f0f9ff',
        padding: '12px 16px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: '1px solid #bae6fd',
      }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#0369a1', marginBottom: '8px' }}>
          📌 Available Variables
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {templates?.variables.map(v => (
            <span 
              key={v.name}
              style={{
                backgroundColor: 'white',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontFamily: 'monospace',
                border: '1px solid #93c5fd',
              }}
              title={v.description}
            >
              {v.name}
            </span>
          ))}
        </div>
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Start GCode Templates */}
        <div>
          <h3 style={{ 
            fontSize: '16px', 
            color: '#059669', 
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            ▶️ Start GCode Templates
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {templates?.start_templates.map((template, index) => (
              <TemplateCard
                key={template.template_key}
                template={template}
                onEdit={() => setEditingTemplate(template)}
                onMoveUp={() => moveTemplate(template.template_key, 'up', 'start')}
                onMoveDown={() => moveTemplate(template.template_key, 'down', 'start')}
                isFirst={index === 0}
                isLast={index === (templates?.start_templates.length ?? 0) - 1}
                reordering={reordering}
              />
            ))}
          </div>
        </div>

        {/* End GCode Templates */}
        <div>
          <h3 style={{ 
            fontSize: '16px', 
            color: '#dc2626', 
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            ⏹️ End GCode Templates
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {templates?.end_templates.map((template, index) => (
              <TemplateCard
                key={template.template_key}
                template={template}
                onEdit={() => setEditingTemplate(template)}
                onMoveUp={() => moveTemplate(template.template_key, 'up', 'end')}
                onMoveDown={() => moveTemplate(template.template_key, 'down', 'end')}
                isFirst={index === 0}
                isLast={index === (templates?.end_templates.length ?? 0) - 1}
                isEndTemplate
                reordering={reordering}
              />
            ))}
          </div>
        </div>
      </div>
        </>
      )}

      {/* Presets Tab Content */}
      {activeTab === 'presets' && (
        <>
          {/* Presets Header */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '20px',
            paddingBottom: '16px',
            borderBottom: '1px solid #e5e7eb'
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', color: '#1f2937' }}>⚙️ Print Presets</h2>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#6b7280' }}>
                Create and manage automation presets for your print jobs
              </p>
            </div>
            <button
              onClick={handleNewPreset}
              style={{
                padding: '10px 20px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              ➕ New Preset
            </button>
          </div>

          {/* Presets Grid */}
          {presetsLoading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
              <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
              Loading presets...
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
              {presets.map(preset => (
                <div
                  key={preset.preset_id}
                  style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '12px',
                    border: preset.is_default ? '2px solid #10b981' : '1px solid #e5e7eb',
                    overflow: 'hidden',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                  }}
                >
                  {/* Preset Header */}
                  <div style={{
                    padding: '16px',
                    borderBottom: '1px solid #e5e7eb',
                    backgroundColor: preset.color + '10',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ 
                        fontSize: '32px',
                        width: '48px',
                        height: '48px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: preset.color + '20',
                        borderRadius: '10px',
                      }}>
                        {preset.icon}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '16px', color: '#1f2937' }}>
                            {preset.name}
                          </span>
                          {preset.is_default && (
                            <span style={{
                              fontSize: '10px',
                              padding: '2px 6px',
                              backgroundColor: '#10b981',
                              color: 'white',
                              borderRadius: '4px',
                              fontWeight: 600,
                            }}>
                              DEFAULT
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
                          {preset.description || 'No description'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Preset Settings */}
                  <div style={{ padding: '12px 16px' }}>
                    <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px', fontWeight: 600 }}>
                      AUTOMATION SETTINGS
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {preset.auto_bed_leveling && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dbeafe', color: '#1d4ed8', borderRadius: '4px' }}>🛏️ Bed Leveling</span>}
                      {preset.flow_calibration && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dbeafe', color: '#1d4ed8', borderRadius: '4px' }}>💧 Flow Cal</span>}
                      {preset.vibration_test && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dbeafe', color: '#1d4ed8', borderRadius: '4px' }}>📳 Vibration</span>}
                      {preset.clean_nozzle && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dbeafe', color: '#1d4ed8', borderRadius: '4px' }}>🧹 Clean Nozzle</span>}
                      {preset.wipe_nozzle && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dcfce7', color: '#15803d', borderRadius: '4px' }}>🧽 Wipe</span>}
                      {preset.nozzle_load_line && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dcfce7', color: '#15803d', borderRadius: '4px' }}>📏 Load Line</span>}
                      {preset.pre_extrude && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#dcfce7', color: '#15803d', borderRadius: '4px' }}>🔄 Pre-Extrude</span>}
                      {preset.timelapse && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#fef3c7', color: '#92400e', borderRadius: '4px' }}>📹 Timelapse</span>}
                      {preset.startup_sound && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#f3e8ff', color: '#7c3aed', borderRadius: '4px' }}>🔔 Start Sound</span>}
                      {preset.end_sound && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#f3e8ff', color: '#7c3aed', borderRadius: '4px' }}>🔔 End Sound</span>}
                      {preset.auto_eject && <span style={{ fontSize: '11px', padding: '3px 8px', backgroundColor: '#fee2e2', color: '#dc2626', borderRadius: '4px' }}>⏏️ Auto Eject</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '16px', marginTop: '12px', fontSize: '12px', color: '#6b7280' }}>
                      <span>🌡️ Cooldown: {preset.cooldown_temp}°C</span>
                      <span>🔥 Preheat: +{preset.preheat_offset}°C</span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div style={{ 
                    padding: '12px 16px',
                    borderTop: '1px solid #e5e7eb',
                    display: 'flex',
                    gap: '8px',
                  }}>
                    <button
                      onClick={() => handleEditPreset(preset)}
                      style={{
                        flex: 1,
                        padding: '8px 12px',
                        backgroundColor: '#f3f4f6',
                        border: '1px solid #d1d5db',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}
                    >
                      ✏️ Edit
                    </button>
                    {!preset.is_default && (
                      <button
                        onClick={() => handleSetDefault(preset)}
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          backgroundColor: '#ecfdf5',
                          border: '1px solid #a7f3d0',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '12px',
                          fontWeight: 500,
                          color: '#059669',
                        }}
                      >
                        ⭐ Set Default
                      </button>
                    )}
                    <button
                      onClick={() => handleDeletePreset(preset)}
                      style={{
                        padding: '8px 12px',
                        backgroundColor: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        color: '#dc2626',
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Preset Form Modal */}
      {showPresetForm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            width: '900px',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 25px 50px rgba(0,0,0,0.25)',
          }}>
            <div style={{
              padding: '24px',
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'linear-gradient(135deg, #f0fdf4 0%, #fef2f2 100%)',
            }}>
              <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>
                {editingPreset ? '✏️ Edit Print Preset' : '➕ Create New Print Preset'}
              </h3>
              <button
                onClick={() => { setShowPresetForm(false); setEditingPreset(null); }}
                style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#6b7280' }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              {/* Name and Icon Row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                    Preset Name
                  </label>
                  <input
                    type="text"
                    value={presetFormData.name}
                    onChange={(e) => setPresetFormData({ ...presetFormData, name: e.target.value })}
                    placeholder="e.g. Quick Print"
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '6px',
                      border: '1px solid #d1d5db',
                      fontSize: '14px',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                    Icon
                  </label>
                  <select
                    value={presetFormData.icon}
                    onChange={(e) => setPresetFormData({ ...presetFormData, icon: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px',
                      borderRadius: '6px',
                      border: '1px solid #d1d5db',
                      fontSize: '20px',
                      textAlign: 'center',
                    }}
                  >
                    <option value="⚡">⚡</option>
                    <option value="🔧">🔧</option>
                    <option value="🎬">🎬</option>
                    <option value="🌙">🌙</option>
                    <option value="🚀">🚀</option>
                    <option value="⭐">⭐</option>
                    <option value="🎯">🎯</option>
                    <option value="💎">💎</option>
                    <option value="🔥">🔥</option>
                    <option value="❄️">❄️</option>
                  </select>
                </div>
              </div>

              {/* Description */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                  Description
                </label>
                <input
                  type="text"
                  value={presetFormData.description}
                  onChange={(e) => setPresetFormData({ ...presetFormData, description: e.target.value })}
                  placeholder="Describe when to use this preset"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    fontSize: '14px',
                  }}
                />
              </div>

              {/* Color */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                  Color
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899', '#06b6d4'].map(color => (
                    <button
                      key={color}
                      onClick={() => setPresetFormData({ ...presetFormData, color })}
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '8px',
                        backgroundColor: color,
                        border: presetFormData.color === color ? '3px solid #1f2937' : '2px solid transparent',
                        cursor: 'pointer',
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Start GCode Settings */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '16px', 
                  fontWeight: 700, 
                  marginBottom: '16px',
                  color: '#059669',
                  padding: '12px 16px',
                  backgroundColor: '#ecfdf5',
                  borderRadius: '10px',
                  border: '2px solid #10b981'
                }}>
                  <span style={{ fontSize: '24px' }}>🚀</span> Start GCode Templates (21)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {[
                    { order: 1, key: 'start_machine', label: 'Start Machine A1', desc: 'Initialize A1 machine with G390/M9001 commands' },
                    { order: 2, key: 'heat_bed_hotend', label: 'Heat Bed & Hotend', desc: 'Start heating heatbed and hotend to initial temperatures' },
                    { order: 3, key: 'startup_sound', label: 'Startup Sound', desc: 'Play startup melody when print begins' },
                    { order: 4, key: 'avoid_end_stop', label: 'Avoid End Stop', desc: 'Move Z axis to avoid end stop issues' },
                    { order: 5, key: 'reset_machine_status', label: 'Reset Machine Status', desc: 'Reset motor currents, feedrate, flowrate and machine status' },
                    { order: 6, key: 'cog_noise_reduction', label: 'Cog Noise Reduction', desc: 'Home X, extrude test, home Z with cog noise reduction' },
                    { order: 7, key: 'ams_slot', label: 'AMS Slot / Prepare Material', desc: 'Select AMS slot, load filament, flush, and prep material' },
                    { order: 8, key: 'flow_calibration', label: 'Auto Extrude Calibration', desc: 'Automatic extrusion calibration for flow accuracy' },
                    { order: 9, key: 'vibration_test', label: 'Mech Mode Fast Check (Vibration Test)', desc: 'Quick vibration/resonance test for mechanical calibration' },
                    { order: 10, key: 'wipe_nozzle', label: 'Wipe Nozzle', desc: 'Clean nozzle by touching and wiping on steel surface' },
                    { order: 11, key: 'clean_nozzle', label: 'Clean Nozzle', desc: 'Deep clean nozzle on exposed steel surface with circular motion' },
                    { order: 12, key: 'brush_material_wipe', label: 'Brush Material Wipe', desc: 'Wipe nozzle using brush material back and forth' },
                    { order: 13, key: 'final_wipe_nozzle', label: 'Final Wipe Nozzle', desc: 'Final nozzle wipe with circular motion on steel surface' },
                    { order: 14, key: 'auto_bed_leveling', label: 'Bed Leveling', desc: 'Automatic bed leveling with G29' },
                    { order: 15, key: 'home_after_wipe', label: 'Home After Wipe', desc: 'Re-home XY after nozzle wipe if not ABS' },
                    { order: 16, key: 'prepare_print', label: 'Prepare Print', desc: 'Final preparation before print starts' },
                    { order: 17, key: 'nozzle_load_line', label: 'Nozzle Load Line', desc: 'Draw purge line at front of bed before print' },
                    { order: 18, key: 'extrude_calibration_test', label: 'Extrude Calibration Test', desc: 'Test extrusion with calibration pattern' },
                    { order: 19, key: 'turn_off_light', label: 'Turn Off Light & Wait', desc: 'Turn off chamber light and wait for start' },
                    { order: 20, key: 'final_start', label: 'Final Start', desc: 'Final positioning and start print' },
                    { order: 21, key: 'pre_extrude', label: 'Pre-Extrude', desc: 'Prime the nozzle before printing' },
                  ].map(setting => {
                    const isChecked = presetFormData[setting.key as keyof PrintPresetCreate] as boolean ?? false;
                    return (
                      <label
                        key={setting.order}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '12px',
                          padding: '12px 14px',
                          backgroundColor: isChecked ? '#f0fdf4' : '#fafafa',
                          borderRadius: '10px',
                          border: isChecked ? '2px solid #86efac' : '2px solid #e5e7eb',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => setPresetFormData({ ...presetFormData, [setting.key]: e.target.checked })}
                          style={{ width: '20px', height: '20px', marginTop: '2px', accentColor: '#10b981' }}
                        />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: isChecked ? '#059669' : '#6b7280' }}>
                            <span style={{ 
                              display: 'inline-block',
                              width: '28px',
                              height: '22px',
                              backgroundColor: '#e5e7eb',
                              borderRadius: '4px',
                              textAlign: 'center',
                              fontSize: '11px',
                              fontWeight: 700,
                              lineHeight: '22px',
                              marginRight: '8px',
                              color: '#4b5563'
                            }}>#{setting.order}</span>
                            {setting.label}
                          </div>
                          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>{setting.desc}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* End GCode Settings */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '16px', 
                  fontWeight: 700, 
                  marginBottom: '16px',
                  color: '#dc2626',
                  padding: '12px 16px',
                  backgroundColor: '#fef2f2',
                  borderRadius: '10px',
                  border: '2px solid #f87171'
                }}>
                  <span style={{ fontSize: '24px' }}>🏁</span> End GCode Templates (6)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {[
                    { order: 1, key: 'end_print_start', label: 'End Print Start', desc: 'Begin end sequence, turn off heaters and fans' },
                    { order: 2, key: 'timelapse', label: 'Timelapse Capture', desc: 'Capture final timelapse frames' },
                    { order: 3, key: 'move_safe_position', label: 'Move to Safe Position', desc: 'Raise Z and move to safe position' },
                    { order: 4, key: 'auto_eject', label: 'Auto Eject', desc: 'Auto push-off print from bed after cooling' },
                    { order: 5, key: 'end_sound', label: 'End Sound', desc: 'Play completion melody' },
                    { order: 6, key: 'end_print_final', label: 'End Print Final', desc: 'Final cleanup, turn off motors and lights' },
                  ].map(setting => {
                    const isChecked = presetFormData[setting.key as keyof PrintPresetCreate] as boolean ?? false;
                    return (
                      <label
                        key={setting.order}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '12px',
                          padding: '12px 14px',
                          backgroundColor: isChecked ? '#fef2f2' : '#fafafa',
                          borderRadius: '10px',
                          border: isChecked ? '2px solid #fca5a5' : '2px solid #e5e7eb',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => setPresetFormData({ ...presetFormData, [setting.key]: e.target.checked })}
                          style={{ width: '20px', height: '20px', marginTop: '2px', accentColor: '#ef4444' }}
                        />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: isChecked ? '#dc2626' : '#6b7280' }}>
                            <span style={{ 
                              display: 'inline-block',
                              width: '28px',
                              height: '22px',
                              backgroundColor: '#fee2e2',
                              borderRadius: '4px',
                              textAlign: 'center',
                              fontSize: '11px',
                              fontWeight: 700,
                              lineHeight: '22px',
                              marginRight: '8px',
                              color: '#991b1b'
                            }}>#{setting.order}</span>
                            {setting.label}
                          </div>
                          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>{setting.desc}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Numeric Settings */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: '1fr 1fr', 
                gap: '20px', 
                marginBottom: '24px',
                padding: '20px',
                backgroundColor: '#f9fafb',
                borderRadius: '12px',
                border: '2px solid #e5e7eb'
              }}>
                <div style={{ 
                  padding: '16px', 
                  backgroundColor: '#f0fdf4', 
                  borderRadius: '10px',
                  border: '2px solid #86efac'
                }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: 700, marginBottom: '10px', color: '#059669' }}>
                    🔥 Preheat Offset (°C)
                    <span style={{ 
                      fontWeight: 500, 
                      fontSize: '11px', 
                      color: 'white',
                      backgroundColor: '#10b981',
                      padding: '2px 8px',
                      borderRadius: '4px'
                    }}>Start</span>
                  </label>
                  <input
                    type="number"
                    value={presetFormData.preheat_offset}
                    onChange={(e) => setPresetFormData({ ...presetFormData, preheat_offset: parseInt(e.target.value) || 0 })}
                    placeholder="0-30"
                    style={{
                      width: '100%',
                      padding: '14px 16px',
                      borderRadius: '8px',
                      border: '2px solid #86efac',
                      fontSize: '18px',
                      fontWeight: 600,
                      textAlign: 'center'
                    }}
                  />
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px', textAlign: 'center' }}>
                    Preheat nozzle earlier to reduce wait time
                  </div>
                </div>
                <div style={{ 
                  padding: '16px', 
                  backgroundColor: '#fef2f2', 
                  borderRadius: '10px',
                  border: '2px solid #fca5a5'
                }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: 700, marginBottom: '10px', color: '#dc2626' }}>
                    🌡️ Cooldown Temp (°C)
                    <span style={{ 
                      fontWeight: 500, 
                      fontSize: '11px', 
                      color: 'white',
                      backgroundColor: '#ef4444',
                      padding: '2px 8px',
                      borderRadius: '4px'
                    }}>End</span>
                  </label>
                  <input
                    type="number"
                    value={presetFormData.cooldown_temp}
                    onChange={(e) => setPresetFormData({ ...presetFormData, cooldown_temp: parseInt(e.target.value) || 0 })}
                    placeholder="0-100"
                    style={{
                      width: '100%',
                      padding: '14px 16px',
                      borderRadius: '8px',
                      border: '2px solid #fca5a5',
                      fontSize: '18px',
                      fontWeight: 600,
                      textAlign: 'center'
                    }}
                  />
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px', textAlign: 'center' }}>
                    Wait until bed cools to this temp before eject
                  </div>
                </div>
              </div>
            </div>

            {/* Form Actions */}
            <div style={{
              padding: '16px 20px',
              borderTop: '1px solid #e5e7eb',
              display: 'flex',
              gap: '12px',
              justifyContent: 'flex-end',
            }}>
              <button
                onClick={() => { setShowPresetForm(false); setEditingPreset(null); }}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSavePreset}
                disabled={saving || !presetFormData.name}
                style={{
                  padding: '10px 24px',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 600,
                  opacity: saving || !presetFormData.name ? 0.5 : 1,
                }}
              >
                {saving ? 'Saving...' : editingPreset ? 'Update Preset' : 'Create Preset'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingTemplate && (
        <EditTemplateModal
          template={editingTemplate}
          onSave={(updates) => updateTemplate(editingTemplate.template_key, updates)}
          onClose={() => setEditingTemplate(null)}
          saving={saving}
        />
      )}

      {/* Preview Modal */}
      {showPreview && previewGcode && (
        <PreviewModal
          startGcode={previewGcode.start}
          endGcode={previewGcode.end}
          settings={previewSettings}
          onSettingsChange={setPreviewSettings}
          onRegenerate={generatePreview}
          onClose={() => setShowPreview(false)}
        />
      )}
    </div>
  );
};

// Template Card Component
// Template hanya untuk edit gcode, tidak ada checkbox enable/disable
// Kontrol fitur (Bed Leveling, Clean Nozzle, dll) ada di Queue Settings
const TemplateCard: React.FC<{
  template: Template;
  onEdit: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst: boolean;
  isLast: boolean;
  isEndTemplate?: boolean;
  reordering?: boolean;
}> = ({ template, onEdit, onMoveUp, onMoveDown, isFirst, isLast, isEndTemplate, reordering }) => {
  // Check if this template is controllable (has corresponding setting in Queue Settings)
  const isControllable = (template as any).controllable === true;
  const settingKey = (template as any).setting_key || '';
  
  return (
    <div style={{
      backgroundColor: 'white',
      border: `1px solid ${isEndTemplate ? '#fecaca' : '#bbf7d0'}`,
      borderRadius: '8px',
      padding: '12px 16px',
      opacity: reordering ? 0.7 : 1,
      transition: 'opacity 0.2s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        {/* Reorder Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <button
            onClick={onMoveUp}
            disabled={isFirst || reordering}
            style={{
              padding: '2px 6px',
              backgroundColor: isFirst ? '#f3f4f6' : '#e0f2fe',
              border: '1px solid #bae6fd',
              borderRadius: '4px',
              cursor: isFirst ? 'not-allowed' : 'pointer',
              fontSize: '10px',
              opacity: isFirst ? 0.4 : 1,
            }}
            title="Move Up"
          >
            ⬆️
          </button>
          <button
            onClick={onMoveDown}
            disabled={isLast || reordering}
            style={{
              padding: '2px 6px',
              backgroundColor: isLast ? '#f3f4f6' : '#e0f2fe',
              border: '1px solid #bae6fd',
              borderRadius: '4px',
              cursor: isLast ? 'not-allowed' : 'pointer',
              fontSize: '10px',
              opacity: isLast ? 0.4 : 1,
            }}
            title="Move Down"
          >
            ⬇️
          </button>
        </div>
        
        {/* Order Number */}
        <div style={{
          backgroundColor: isEndTemplate ? '#fef2f2' : '#ecfdf5',
          color: isEndTemplate ? '#dc2626' : '#059669',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600,
          minWidth: '28px',
          textAlign: 'center',
        }}>
          #{template.order}
        </div>
        
        {/* Content */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ 
              fontWeight: 600, 
              fontSize: '14px', 
              color: '#1f2937'
            }}>
              {template.name}
            </span>
            {isControllable && (
              <span style={{
                fontSize: '10px',
                backgroundColor: '#dbeafe',
                color: '#1d4ed8',
                padding: '2px 6px',
                borderRadius: '4px',
                fontWeight: 500,
              }}>
                ⚙️ {settingKey}
              </span>
            )}
          </div>
          <p style={{ 
            margin: '4px 0 0', 
            fontSize: '12px', 
            color: '#6b7280',
          }}>
            {template.description}
          </p>
        </div>
        
        {/* Edit Button */}
        <button
          onClick={onEdit}
          style={{
            padding: '4px 10px',
            backgroundColor: '#f3f4f6',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          ✏️ Edit
        </button>
      </div>
    </div>
  );
};

// Edit Template Modal
const EditTemplateModal: React.FC<{
  template: Template;
  onSave: (updates: Partial<Template>) => void;
  onClose: () => void;
  saving: boolean;
}> = ({ template, onSave, onClose, saving }) => {
  const [gcode, setGcode] = useState(template.gcode);
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        width: '800px',
        maxHeight: '90vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <h3 style={{ margin: 0, fontSize: '18px' }}>✏️ Edit Template: {template.name}</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#6b7280',
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '20px', flex: 1, overflow: 'auto' }}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px',
              }}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Description
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              GCode
            </label>
            <textarea
              value={gcode}
              onChange={(e) => setGcode(e.target.value)}
              style={{
                width: '100%',
                height: '400px',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '13px',
                fontFamily: 'monospace',
                resize: 'vertical',
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '8px',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 20px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onSave({ name, description, gcode })}
            disabled={saving}
            style={{
              padding: '8px 20px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 500,
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? '⏳ Saving...' : '💾 Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Preview Modal
const PreviewModal: React.FC<{
  startGcode: string;
  endGcode: string;
  settings: any;
  onSettingsChange: (settings: any) => void;
  onRegenerate: () => void;
  onClose: () => void;
}> = ({ startGcode, endGcode, settings, onSettingsChange, onRegenerate, onClose }) => {
  const [activeTab, setActiveTab] = useState<'start' | 'end'>('start');

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        width: '1000px',
        maxHeight: '90vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <h3 style={{ margin: 0, fontSize: '18px' }}>👁️ GCode Preview</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#6b7280',
            }}
          >
            ×
          </button>
        </div>

        {/* Settings Bar */}
        <div style={{
          padding: '12px 20px',
          backgroundColor: '#f9fafb',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          gap: '16px',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280' }}>Nozzle:</label>
            <input
              type="number"
              value={settings.nozzle_temp}
              onChange={(e) => onSettingsChange({ ...settings, nozzle_temp: parseInt(e.target.value) })}
              style={{ width: '60px', padding: '4px', borderRadius: '4px', border: '1px solid #d1d5db' }}
            />
            <span style={{ fontSize: '12px', color: '#6b7280' }}>°C</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280' }}>Bed:</label>
            <input
              type="number"
              value={settings.bed_temp}
              onChange={(e) => onSettingsChange({ ...settings, bed_temp: parseInt(e.target.value) })}
              style={{ width: '60px', padding: '4px', borderRadius: '4px', border: '1px solid #d1d5db' }}
            />
            <span style={{ fontSize: '12px', color: '#6b7280' }}>°C</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280' }}>Filament:</label>
            <select
              value={settings.filament_type}
              onChange={(e) => onSettingsChange({ ...settings, filament_type: e.target.value })}
              style={{ padding: '4px', borderRadius: '4px', border: '1px solid #d1d5db' }}
            >
              <option value="PLA">PLA</option>
              <option value="PETG">PETG</option>
              <option value="ABS">ABS</option>
              <option value="TPU">TPU</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280' }}>AMS Slot:</label>
            <select
              value={settings.ams_slot}
              onChange={(e) => onSettingsChange({ ...settings, ams_slot: parseInt(e.target.value) })}
              style={{ padding: '4px', borderRadius: '4px', border: '1px solid #d1d5db' }}
            >
              <option value={0}>0</option>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280' }}>
              <input
                type="checkbox"
                checked={settings.filament_already_loaded}
                onChange={(e) => onSettingsChange({ ...settings, filament_already_loaded: e.target.checked })}
              />
              {' '}Filament Already Loaded
            </label>
          </div>
          <button
            onClick={onRegenerate}
            style={{
              padding: '4px 12px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
            }}
          >
            🔄 Regenerate
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb' }}>
          <button
            onClick={() => setActiveTab('start')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              backgroundColor: activeTab === 'start' ? '#ecfdf5' : 'transparent',
              borderBottom: activeTab === 'start' ? '2px solid #059669' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'start' ? 600 : 400,
              color: activeTab === 'start' ? '#059669' : '#6b7280',
            }}
          >
            ▶️ Start GCode ({startGcode.split('\n').length} lines)
          </button>
          <button
            onClick={() => setActiveTab('end')}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              backgroundColor: activeTab === 'end' ? '#fef2f2' : 'transparent',
              borderBottom: activeTab === 'end' ? '2px solid #dc2626' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'end' ? 600 : 400,
              color: activeTab === 'end' ? '#dc2626' : '#6b7280',
            }}
          >
            ⏹️ End GCode ({endGcode.split('\n').length} lines)
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          <pre style={{
            margin: 0,
            padding: '16px',
            backgroundColor: '#1f2937',
            color: '#e5e7eb',
            borderRadius: '8px',
            fontSize: '12px',
            fontFamily: 'monospace',
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            {activeTab === 'start' ? startGcode : endGcode}
          </pre>
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 20px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default GCodeTemplates;
