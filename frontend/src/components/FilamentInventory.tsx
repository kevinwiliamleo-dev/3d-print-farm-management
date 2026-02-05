import React, { useState, useEffect, useCallback } from 'react';
import { printFarmClient, FilamentProfile, FilamentProfileCreate } from '../api/client';

// Preset data untuk berbagai kombinasi brand + material
const filamentPresets: Record<string, Record<string, Partial<FilamentProfileCreate>>> = {
  'Bambu Lab': {
    'PLA Basic': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 220,
      bedTempMin: 35, bedTempMax: 45, bedTempDefault: 55,
      maxVolumetricSpeed: 21, kValue: 0.020, density: 1.24,
      dryingTemp: 55, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA Matte': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 220,
      bedTempMin: 35, bedTempMax: 45, bedTempDefault: 55,
      maxVolumetricSpeed: 21, kValue: 0.020, density: 1.31,
      dryingTemp: 55, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA-CF': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 220,
      bedTempMin: 35, bedTempMax: 45, bedTempDefault: 55,
      maxVolumetricSpeed: 18, kValue: 0.020, density: 1.26,
      dryingTemp: 55, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: true,
    },
    'PETG Basic': {
      nozzleTempMin: 230, nozzleTempMax: 270, nozzleTempDefault: 255,
      bedTempMin: 65, bedTempMax: 80, bedTempDefault: 70,
      maxVolumetricSpeed: 15, kValue: 0.035, density: 1.27,
      dryingTemp: 65, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PETG-CF': {
      nozzleTempMin: 230, nozzleTempMax: 270, nozzleTempDefault: 255,
      bedTempMin: 65, bedTempMax: 80, bedTempDefault: 70,
      maxVolumetricSpeed: 18, kValue: 0.030, density: 1.29,
      dryingTemp: 65, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: true,
    },
    'ABS': {
      nozzleTempMin: 240, nozzleTempMax: 270, nozzleTempDefault: 260,
      bedTempMin: 90, bedTempMax: 100, bedTempDefault: 90,
      maxVolumetricSpeed: 18, kValue: 0.025, density: 1.05,
      dryingTemp: 80, dryingTime: 8,
      requiresEnclosure: true, requiresHardenedNozzle: false,
    },
    'ASA': {
      nozzleTempMin: 240, nozzleTempMax: 270, nozzleTempDefault: 260,
      bedTempMin: 90, bedTempMax: 100, bedTempDefault: 90,
      maxVolumetricSpeed: 18, kValue: 0.025, density: 1.07,
      dryingTemp: 80, dryingTime: 8,
      requiresEnclosure: true, requiresHardenedNozzle: false,
    },
    'PC': {
      nozzleTempMin: 260, nozzleTempMax: 290, nozzleTempDefault: 270,
      bedTempMin: 100, bedTempMax: 110, bedTempDefault: 100,
      maxVolumetricSpeed: 16, kValue: 0.030, density: 1.19,
      dryingTemp: 80, dryingTime: 8,
      requiresEnclosure: true, requiresHardenedNozzle: false,
    },
    'TPU 95A': {
      nozzleTempMin: 210, nozzleTempMax: 240, nozzleTempDefault: 230,
      bedTempMin: 30, bedTempMax: 60, bedTempDefault: 35,
      maxVolumetricSpeed: 3.5, kValue: 0.200, density: 1.22,
      dryingTemp: 70, dryingTime: 8,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PAHT-CF': {
      nozzleTempMin: 260, nozzleTempMax: 300, nozzleTempDefault: 280,
      bedTempMin: 90, bedTempMax: 110, bedTempDefault: 100,
      maxVolumetricSpeed: 18, kValue: 0.025, density: 1.24,
      dryingTemp: 80, dryingTime: 12,
      requiresEnclosure: true, requiresHardenedNozzle: true,
    },
  },
  'eSUN': {
    'PLA Basic': {
      nozzleTempMin: 205, nozzleTempMax: 225, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 20, kValue: 0.022, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA+': {
      nozzleTempMin: 205, nozzleTempMax: 225, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 20, kValue: 0.022, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'ePLA-Matte': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 210,
      bedTempMin: 50, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 18, kValue: 0.025, density: 1.28,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PETG': {
      nozzleTempMin: 230, nozzleTempMax: 250, nozzleTempDefault: 240,
      bedTempMin: 70, bedTempMax: 85, bedTempDefault: 75,
      maxVolumetricSpeed: 15, kValue: 0.040, density: 1.23,
      dryingTemp: 65, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'ABS+': {
      nozzleTempMin: 230, nozzleTempMax: 270, nozzleTempDefault: 250,
      bedTempMin: 90, bedTempMax: 110, bedTempDefault: 100,
      maxVolumetricSpeed: 15, kValue: 0.025, density: 1.06,
      dryingTemp: 70, dryingTime: 6,
      requiresEnclosure: true, requiresHardenedNozzle: false,
    },
    'ePA-CF': {
      nozzleTempMin: 240, nozzleTempMax: 260, nozzleTempDefault: 255,
      bedTempMin: 70, bedTempMax: 90, bedTempDefault: 80,
      maxVolumetricSpeed: 10, kValue: 0.030, density: 1.24,
      dryingTemp: 80, dryingTime: 10,
      requiresEnclosure: true, requiresHardenedNozzle: true,
    },
    'TPU 95A': {
      nozzleTempMin: 210, nozzleTempMax: 240, nozzleTempDefault: 225,
      bedTempMin: 0, bedTempMax: 60, bedTempDefault: 50,
      maxVolumetricSpeed: 3, kValue: 0.250, density: 1.21,
      dryingTemp: 60, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA-LW': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 210,
      bedTempMin: 45, bedTempMax: 60, bedTempDefault: 50,
      maxVolumetricSpeed: 8, kValue: 0.000, density: 0.6,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
  },
  'Sunlu': {
    'PLA+ 2.0': {
      nozzleTempMin: 205, nozzleTempMax: 235, nozzleTempDefault: 215,
      bedTempMin: 55, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 20, kValue: 0.025, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA Matte': {
      nozzleTempMin: 185, nozzleTempMax: 205, nozzleTempDefault: 195,
      bedTempMin: 40, bedTempMax: 60, bedTempDefault: 50,
      maxVolumetricSpeed: 22, kValue: 0.020, density: 1.24,
      dryingTemp: 40, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA Silk': {
      nozzleTempMin: 205, nozzleTempMax: 225, nozzleTempDefault: 215,
      bedTempMin: 55, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 12, kValue: 0.035, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PETG': {
      nozzleTempMin: 220, nozzleTempMax: 250, nozzleTempDefault: 235,
      bedTempMin: 70, bedTempMax: 80, bedTempDefault: 75,
      maxVolumetricSpeed: 14, kValue: 0.040, density: 1.27,
      dryingTemp: 65, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'TPU High Flow': {
      nozzleTempMin: 205, nozzleTempMax: 230, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 5, kValue: 0.180, density: 1.21,
      dryingTemp: 55, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA Wood': {
      nozzleTempMin: 190, nozzleTempMax: 220, nozzleTempDefault: 205,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 12, kValue: 0.030, density: 0.8,
      dryingTemp: 50, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: true,
    },
    'PLA+': {
      nozzleTempMin: 200, nozzleTempMax: 235, nozzleTempDefault: 215,
      bedTempMin: 55, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 18, kValue: 0.028, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'High Speed Matt PETG': {
      nozzleTempMin: 230, nozzleTempMax: 250, nozzleTempDefault: 240,
      bedTempMin: 70, bedTempMax: 85, bedTempDefault: 80,
      maxVolumetricSpeed: 18, kValue: 0.038, density: 1.27,
      dryingTemp: 65, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'TPU Silk': {
      nozzleTempMin: 200, nozzleTempMax: 230, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 55,
      maxVolumetricSpeed: 4, kValue: 0.200, density: 1.21,
      dryingTemp: 55, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
  },
  'Anycubic': {
    'PLA Standard': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 200,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 15, kValue: 0.030, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'High Speed PLA': {
      nozzleTempMin: 200, nozzleTempMax: 230, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 70, bedTempDefault: 60,
      maxVolumetricSpeed: 22, kValue: 0.025, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'Silk PLA': {
      nozzleTempMin: 195, nozzleTempMax: 220, nozzleTempDefault: 205,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 12, kValue: 0.035, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PETG': {
      nozzleTempMin: 220, nozzleTempMax: 250, nozzleTempDefault: 240,
      bedTempMin: 70, bedTempMax: 90, bedTempDefault: 80,
      maxVolumetricSpeed: 15, kValue: 0.040, density: 1.27,
      dryingTemp: 65, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
  },
  'Elegoo': {
    'PLA': {
      nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 205,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 15, kValue: 0.030, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PLA+': {
      nozzleTempMin: 200, nozzleTempMax: 235, nozzleTempDefault: 215,
      bedTempMin: 50, bedTempMax: 65, bedTempDefault: 60,
      maxVolumetricSpeed: 16, kValue: 0.028, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'Silk PLA': {
      nozzleTempMin: 195, nozzleTempMax: 220, nozzleTempDefault: 210,
      bedTempMin: 50, bedTempMax: 60, bedTempDefault: 60,
      maxVolumetricSpeed: 12, kValue: 0.035, density: 1.24,
      dryingTemp: 45, dryingTime: 4,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
    'PETG': {
      nozzleTempMin: 220, nozzleTempMax: 250, nozzleTempDefault: 235,
      bedTempMin: 70, bedTempMax: 85, bedTempDefault: 75,
      maxVolumetricSpeed: 14, kValue: 0.040, density: 1.27,
      dryingTemp: 65, dryingTime: 6,
      requiresEnclosure: false, requiresHardenedNozzle: false,
    },
  },
};

const availableBrands = Object.keys(filamentPresets);

// Warna umum untuk filament
const commonColors: { name: string; hex: string; isTransparent?: boolean }[] = [
  { name: 'White', hex: 'FFFFFFFF' },
  { name: 'Black', hex: '000000FF' },
  { name: 'Transparent Blue', hex: '4A90D9AA', isTransparent: true },
  { name: 'Transparent Red', hex: 'FF4444AA', isTransparent: true },
  { name: 'Transparent Green', hex: '44FF44AA', isTransparent: true },
  { name: 'Red', hex: 'FF0000FF' },
  { name: 'Blue', hex: '0066FFFF' },
  { name: 'Light Blue', hex: '87CEEBFF' },
  { name: 'Sky Blue', hex: '00BFFFFF' },
  { name: 'Green', hex: '00CC00FF' },
  { name: 'Sea Green', hex: '2E8B57FF' },
  { name: 'Yellow', hex: 'FFFF00FF' },
  { name: 'Orange', hex: 'FF6600FF' },
  { name: 'Purple', hex: '9900FFFF' },
  { name: 'Magenta', hex: 'FF00FFFF' },
  { name: 'Pink', hex: 'FF66B2FF' },
  { name: 'Grey', hex: '808080FF' },
  { name: 'Light Grey', hex: 'D3D3D3FF' },
  { name: 'Silver', hex: 'C0C0C0FF' },
  { name: 'Gold', hex: 'FFD700FF' },
  { name: 'Brown', hex: '8B4513FF' },
  { name: 'Beige', hex: 'F5F5DCFF' },
  { name: 'Wood', hex: 'DEB887FF' },
  { name: 'Cream White', hex: 'FFFDD0FF' },
  { name: 'Holly Green', hex: '2E8B57FF' },
  { name: 'Clear', hex: 'F5F5F5AA', isTransparent: true },
];

interface SimpleFormData {
  brand: string;
  materialType: string;
  colorHex: string;
  colorName: string;
  spoolWeight: number;
  stockCount: number;
  notes: string;
}

const defaultSimpleForm: SimpleFormData = {
  brand: 'Bambu Lab',
  materialType: 'PLA Basic',
  colorHex: 'FFFFFFFF',
  colorName: 'White',
  spoolWeight: 1000,
  stockCount: 1,
  notes: '',
};

// Checkered pattern for transparent colors
const checkeredPattern = `
  linear-gradient(45deg, #808080 25%, transparent 25%),
  linear-gradient(-45deg, #808080 25%, transparent 25%),
  linear-gradient(45deg, transparent 75%, #808080 75%),
  linear-gradient(-45deg, transparent 75%, #808080 75%)
`;

// Helper to check if color is transparent
const isTransparentColor = (colorHex: string): boolean => {
  if (colorHex === 'TRANSPARENT') return true;
  // Check alpha channel (last 2 chars) - if less than FF, it's semi-transparent
  if (colorHex.length === 8) {
    const alpha = parseInt(colorHex.substring(6, 8), 16);
    return alpha < 200; // Less than ~78% opacity
  }
  return false;
};

// Color preview component
const ColorPreview: React.FC<{ colorHex: string; size?: number }> = ({ colorHex, size = 24 }) => {
  const isTransparent = isTransparentColor(colorHex);
  
  // For fully transparent, show checkered pattern only
  if (colorHex === 'TRANSPARENT') {
    return (
      <div 
        style={{
          width: size,
          height: size,
          background: checkeredPattern,
          backgroundSize: `${size/3}px ${size/3}px`,
          backgroundPosition: `0 0, 0 ${size/6}px, ${size/6}px -${size/6}px, -${size/6}px 0px`,
          borderRadius: '4px',
          border: '1px solid #d1d5db',
          flexShrink: 0,
        }}
      />
    );
  }
  
  // Convert RRGGBBAA to CSS color
  const cssColor = colorHex.length >= 6 
    ? `#${colorHex.substring(0, 6)}` 
    : '#FFFFFF';
  
  // For semi-transparent colors, show checkered pattern behind
  if (isTransparent) {
    const alpha = colorHex.length === 8 ? parseInt(colorHex.substring(6, 8), 16) / 255 : 1;
    return (
      <div 
        style={{
          width: size,
          height: size,
          borderRadius: '4px',
          border: '1px solid #d1d5db',
          flexShrink: 0,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Checkered background */}
        <div style={{
          position: 'absolute',
          inset: 0,
          background: checkeredPattern,
          backgroundSize: `${size/3}px ${size/3}px`,
          backgroundPosition: `0 0, 0 ${size/6}px, ${size/6}px -${size/6}px, -${size/6}px 0px`,
        }} />
        {/* Color overlay with transparency */}
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: cssColor,
          opacity: alpha,
        }} />
      </div>
    );
  }
  
  return (
    <div 
      style={{
        width: size,
        height: size,
        backgroundColor: cssColor,
        borderRadius: '4px',
        border: '1px solid #d1d5db',
        flexShrink: 0,
      }}
    />
  );
};

export const FilamentInventory: React.FC = () => {
  const [filaments, setFilaments] = useState<FilamentProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<SimpleFormData>(defaultSimpleForm);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [filterMaterial, setFilterMaterial] = useState<string>('');
  const [filterBrand, setFilterBrand] = useState<string>('');
  const [materials, setMaterials] = useState<string[]>([]);
  const [brands, setBrands] = useState<string[]>([]);
  const [history, setHistory] = useState<{action: string; name: string; date: string}[]>([]);

  // Get available materials for selected brand
  const availableMaterials = formData.brand && filamentPresets[formData.brand] 
    ? Object.keys(filamentPresets[formData.brand]) 
    : [];

  const loadFilaments = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await printFarmClient.getAllFilaments();
      setFilaments(data);
    } catch (err) {
      console.error('Failed to load filaments:', err);
      setMessage({ type: 'error', text: 'Failed to load filaments' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadFilters = useCallback(async () => {
    try {
      const [mats, brnds] = await Promise.all([
        printFarmClient.getFilamentMaterials(),
        printFarmClient.getFilamentBrands(),
      ]);
      setMaterials(mats);
      setBrands(brnds);
    } catch (err) {
      console.error('Failed to load filters:', err);
    }
  }, []);

  useEffect(() => {
    loadFilaments();
    loadFilters();
    loadHistory();
  }, [loadFilaments, loadFilters]);

  // Load history from localStorage
  const loadHistory = () => {
    try {
      const saved = localStorage.getItem('filament_history');
      if (saved) setHistory(JSON.parse(saved));
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  // Add entry to history
  const addHistoryEntry = (action: string, name: string) => {
    const newEntry = {
      action,
      name,
      date: new Date().toLocaleString('id-ID'),
    };
    const updated = [newEntry, ...history].slice(0, 50); // Keep last 50 entries
    setHistory(updated);
    localStorage.setItem('filament_history', JSON.stringify(updated));
  };

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const handleOpenModal = (filament?: FilamentProfile) => {
    if (filament) {
      // Find color name from hex
      const colorMatch = commonColors.find(c => c.hex === filament.colorHex);
      setEditingId(filament.id);
      setFormData({
        brand: filament.brand,
        materialType: filament.materialType,
        colorHex: filament.colorHex,
        colorName: colorMatch?.name || 'Custom',
        spoolWeight: filament.spoolWeight ?? 1000,
        stockCount: filament.stockCount ?? 1,
        notes: filament.notes || '',
      });
    } else {
      setEditingId(null);
      setFormData(defaultSimpleForm);
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingId(null);
    setFormData(defaultSimpleForm);
  };

  const handleBrandChange = (newBrand: string) => {
    const availMats = filamentPresets[newBrand] ? Object.keys(filamentPresets[newBrand]) : [];
    const newMaterial = availMats.includes(formData.materialType) ? formData.materialType : (availMats[0] || 'PLA Basic');
    setFormData({ ...formData, brand: newBrand, materialType: newMaterial });
  };

  // Default preset fallback
  const defaultPreset = {
    nozzleTempMin: 190, nozzleTempMax: 230, nozzleTempDefault: 210,
    bedTempMin: 50, bedTempMax: 65, bedTempDefault: 55,
    maxVolumetricSpeed: 15, kValue: 0.02, density: 1.24,
    dryingTemp: 50, dryingTime: 4,
    requiresEnclosure: false, requiresHardenedNozzle: false,
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Get preset data with fallback
      const preset = filamentPresets[formData.brand]?.[formData.materialType] || defaultPreset;
      
      // Generate name automatically
      const autoName = `${formData.brand} ${formData.materialType} - ${formData.colorName}`;
      
      // Check if filament with same brand, material and color already exists
      if (!editingId) {
        const existing = filaments.find(f => 
          f.brand === formData.brand && 
          f.materialType === formData.materialType && 
          f.colorHex === formData.colorHex
        );
        
        if (existing) {
          // Add 1000g per spool to existing filament
          const gramsToAdd = formData.stockCount * 1000;
          await printFarmClient.addFilamentStock(existing.id, gramsToAdd);
          setMessage({ type: 'success', text: `Ditambahkan ${formData.stockCount} spool (+${gramsToAdd}g) ke ${existing.name}` });
          addHistoryEntry('Added Stock', `${existing.name} (+${formData.stockCount} roll)`);
          await loadFilaments();
          await loadFilters();
          handleCloseModal();
          return;
        }
      }
      
      // Build full payload with preset values
      const payload: FilamentProfileCreate = {
        name: autoName,
        brand: formData.brand,
        materialType: formData.materialType,
        colorHex: formData.colorHex,
        diameter: 1.75,
        spoolWeight: formData.stockCount * 1000, // 1 spool = 1000g
        stockCount: formData.stockCount,
        notes: formData.notes,
        // Auto-filled from preset
        nozzleTempMin: preset.nozzleTempMin,
        nozzleTempMax: preset.nozzleTempMax,
        nozzleTempDefault: preset.nozzleTempDefault,
        bedTempMin: preset.bedTempMin,
        bedTempMax: preset.bedTempMax,
        bedTempDefault: preset.bedTempDefault,
        maxVolumetricSpeed: preset.maxVolumetricSpeed,
        kValue: preset.kValue,
        density: preset.density,
        dryingTemp: preset.dryingTemp,
        dryingTime: preset.dryingTime,
        requiresEnclosure: preset.requiresEnclosure,
        requiresHardenedNozzle: preset.requiresHardenedNozzle,
      };

      if (editingId) {
        await printFarmClient.updateFilament(editingId, payload);
        setMessage({ type: 'success', text: 'Filament updated successfully' });
        addHistoryEntry('Updated', autoName);
      } else {
        await printFarmClient.createFilament(payload);
        setMessage({ type: 'success', text: 'Filament added successfully' });
        addHistoryEntry('Added', autoName);
      }

      await loadFilaments();
      await loadFilters();
      handleCloseModal();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to save filament' });
    }
  };

  const handleDelete = async (id: number) => {
    const filament = filaments.find(f => f.id === id);
    if (!window.confirm('Are you sure you want to delete this filament?')) return;
    try {
      await printFarmClient.deleteFilament(id);
      setMessage({ type: 'success', text: 'Filament deleted' });
      if (filament) addHistoryEntry('Deleted', filament.name);
      await loadFilaments();
      await loadFilters();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete filament' });
    }
  };

  const handleStockChange = async (id: number, action: 'add' | 'use') => {
    try {
      if (action === 'add') {
        await printFarmClient.addFilamentStock(id, 1);
      } else {
        await printFarmClient.useFilamentStock(id, 1);
      }
      await loadFilaments();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update stock' });
    }
  };

  // Filter filaments
  const filteredFilaments = filaments.filter(f => {
    if (filterMaterial && f.materialType !== filterMaterial) return false;
    if (filterBrand && f.brand !== filterBrand) return false;
    return true;
  });

  // Group by material type
  const groupedFilaments = filteredFilaments.reduce((acc, f) => {
    if (!acc[f.materialType]) acc[f.materialType] = [];
    acc[f.materialType].push(f);
    return acc;
  }, {} as Record<string, FilamentProfile[]>);

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    boxSizing: 'border-box',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: '#374151',
    marginBottom: '4px',
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: '#1f2937' }}>
            🧵 Filament Inventory
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#6b7280' }}>
            Manage your filament stock and profiles
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => setShowHistory(!showHistory)}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              backgroundColor: showHistory ? '#f3f4f6' : '#ffffff',
              color: '#374151',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            📜 History
          </button>
          <button
            onClick={() => handleOpenModal()}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            ➕ Add Filament
          </button>
        </div>
      </div>

      {/* Toast Message */}
      {message && (
        <div style={{
          position: 'fixed',
          top: '80px',
          right: '24px',
          padding: '12px 20px',
          borderRadius: '8px',
          backgroundColor: message.type === 'success' ? '#d1fae5' : '#fee2e2',
          color: message.type === 'success' ? '#065f46' : '#991b1b',
          fontSize: '14px',
          fontWeight: 500,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          zIndex: 1000,
        }}>
          {message.type === 'success' ? '✓' : '✕'} {message.text}
        </div>
      )}

      {/* History Panel */}
      {showHistory && (
        <div style={{
          marginBottom: '24px',
          padding: '16px 20px',
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#1f2937' }}>
              📜 Inventory History
            </h3>
            <button
              onClick={() => {
                if (window.confirm('Clear all history?')) {
                  setHistory([]);
                  localStorage.removeItem('filament_history');
                }
              }}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: '#fee2e2',
                color: '#dc2626',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              🗑️ Clear
            </button>
          </div>
          {history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280', fontSize: '14px' }}>
              No history yet
            </div>
          ) : (
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {history.map((entry, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 0',
                    borderBottom: idx < history.length - 1 ? '1px solid #f3f4f6' : 'none',
                  }}
                >
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                    backgroundColor: entry.action === 'Added' ? '#d1fae5' : entry.action === 'Updated' ? '#dbeafe' : '#fee2e2',
                    color: entry.action === 'Added' ? '#065f46' : entry.action === 'Updated' ? '#1d4ed8' : '#dc2626',
                  }}>
                    {entry.action}
                  </span>
                  <span style={{ flex: 1, fontSize: '14px', color: '#374151' }}>{entry.name}</span>
                  <span style={{ fontSize: '12px', color: '#9ca3af' }}>{entry.date}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div style={{ 
        display: 'flex', 
        gap: '16px', 
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: '#f9fafb',
        borderRadius: '8px',
      }}>
        <div>
          <label style={labelStyle}>Material Type</label>
          <select
            value={filterMaterial}
            onChange={(e) => setFilterMaterial(e.target.value)}
            style={{ ...inputStyle, width: '160px' }}
          >
            <option value="">All Materials</option>
            {materials.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Brand</label>
          <select
            value={filterBrand}
            onChange={(e) => setFilterBrand(e.target.value)}
            style={{ ...inputStyle, width: '160px' }}
          >
            <option value="">All Brands</option>
            {brands.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'flex-end' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>
            {filteredFilaments.length} filament(s)
          </span>
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#6b7280' }}>
          Loading filaments...
        </div>
      ) : filteredFilaments.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '60px',
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '2px dashed #e5e7eb',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🧵</div>
          <div style={{ fontSize: '16px', color: '#374151', fontWeight: 500, marginBottom: '8px' }}>
            No filaments in inventory
          </div>
          <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '20px' }}>
            Add your first filament to get started
          </div>
          <button
            onClick={() => handleOpenModal()}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Add Filament
          </button>
        </div>
      ) : (
        /* Filament Grid by Material */
        Object.entries(groupedFilaments).map(([material, items]) => (
          <div key={material} style={{ marginBottom: '32px' }}>
            <h3 style={{ 
              margin: '0 0 16px', 
              fontSize: '16px', 
              fontWeight: 600, 
              color: '#1f2937',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <span style={{
                padding: '4px 12px',
                backgroundColor: '#e0e7ff',
                color: '#3730a3',
                borderRadius: '20px',
                fontSize: '13px',
              }}>
                {material}
              </span>
              <span style={{ fontSize: '13px', color: '#6b7280', fontWeight: 400 }}>
                ({items.length})
              </span>
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '16px',
            }}>
              {items.map(filament => (
                <div
                  key={filament.id}
                  style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid #e5e7eb',
                    padding: '16px',
                    transition: 'box-shadow 0.2s',
                  }}
                >
                  {/* Header */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
                    <ColorPreview colorHex={filament.colorHex} size={40} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        fontWeight: 600, 
                        fontSize: '15px', 
                        color: '#1f2937',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {filament.name}
                      </div>
                      <div style={{ fontSize: '13px', color: '#6b7280' }}>
                        {filament.brand}
                      </div>
                    </div>
                    {/* Roll Count Badge */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 10px',
                      backgroundColor: (filament.stockCount ?? 1) > 1 ? '#dbeafe' : '#f3f4f6',
                      borderRadius: '20px',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: (filament.stockCount ?? 1) > 1 ? '#1d4ed8' : '#6b7280',
                    }}>
                      🧻 {filament.stockCount ?? 1} roll
                    </div>
                  </div>

                  {/* Remaining Weight Info */}
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px',
                    marginBottom: '12px',
                    padding: '8px 12px',
                    backgroundColor: (filament.spoolWeight ?? 0) >= 1000 ? '#f0fdf4' : (filament.spoolWeight ?? 0) >= 500 ? '#fefce8' : '#fef2f2',
                    borderRadius: '8px',
                  }}>
                    <span style={{ fontSize: '18px' }}>⚖️</span>
                    <div>
                      <span style={{ 
                        color: (filament.spoolWeight ?? 0) >= 1000 ? '#166534' : (filament.spoolWeight ?? 0) >= 500 ? '#a16207' : '#dc2626', 
                        fontWeight: 600,
                        fontSize: '16px',
                      }}>
                        {(filament.spoolWeight ?? 0) >= 1000 
                          ? `${((filament.spoolWeight ?? 0) / 1000).toFixed(1)} kg` 
                          : `${filament.spoolWeight ?? 0}g`}
                      </span>
                      <span style={{ color: '#6b7280' }}> tersisa</span>
                    </div>
                  </div>

                  {/* Properties */}
                  <div style={{ 
                    display: 'flex', 
                    gap: '6px', 
                    flexWrap: 'wrap',
                    marginBottom: '12px',
                  }}>
                    {filament.diameter && (
                      <span style={{
                        padding: '2px 8px',
                        backgroundColor: '#f3f4f6',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: '#6b7280',
                      }}>
                        Ø {filament.diameter}mm
                      </span>
                    )}
                    {filament.kValue && (
                      <span style={{
                        padding: '2px 8px',
                        backgroundColor: '#f3f4f6',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: '#6b7280',
                      }}>
                        K: {filament.kValue}
                      </span>
                    )}
                    {filament.requiresEnclosure && (
                      <span style={{
                        padding: '2px 8px',
                        backgroundColor: '#fef3c7',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: '#92400e',
                      }}>
                        🔒 Enclosure
                      </span>
                    )}
                    {filament.requiresHardenedNozzle && (
                      <span style={{
                        padding: '2px 8px',
                        backgroundColor: '#fee2e2',
                        borderRadius: '4px',
                        fontSize: '11px',
                        color: '#991b1b',
                      }}>
                        ⚙️ Hardened Nozzle
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid #f3f4f6', paddingTop: '12px' }}>
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={() => handleOpenModal(filament)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: '#3b82f6',
                        color: '#ffffff',
                        fontSize: '12px',
                        cursor: 'pointer',
                      }}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => handleDelete(filament.id)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: '#ef4444',
                        color: '#ffffff',
                        fontSize: '12px',
                        cursor: 'pointer',
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            padding: '24px',
            width: '600px',
            maxWidth: '90vw',
            maxHeight: '85vh',
            overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
                {editingId ? '✏️ Edit Filament' : '➕ Add New Filament'}
              </h3>
              <button
                onClick={handleCloseModal}
                style={{
                  border: 'none',
                  background: 'none',
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: '#9ca3af',
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Step 1: Brand */}
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>1️⃣ Brand / Merek</label>
                <select
                  value={formData.brand}
                  onChange={e => handleBrandChange(e.target.value)}
                  style={{ ...inputStyle, fontSize: '16px', padding: '12px' }}
                >
                  {availableBrands.map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>

              {/* Step 2: Material Type */}
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>2️⃣ Jenis Material</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {availableMaterials.map(m => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setFormData({ ...formData, materialType: m })}
                      style={{
                        padding: '10px 20px',
                        borderRadius: '8px',
                        border: formData.materialType === m ? '2px solid #3b82f6' : '1px solid #d1d5db',
                        backgroundColor: formData.materialType === m ? '#eff6ff' : '#ffffff',
                        color: formData.materialType === m ? '#1d4ed8' : '#374151',
                        fontSize: '14px',
                        fontWeight: formData.materialType === m ? 600 : 400,
                        cursor: 'pointer',
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              {/* Step 3: Color */}
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>3️⃣ Warna</label>
                
                {/* Solid Colors */}
                <div style={{ marginBottom: '12px' }}>
                  <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: 500, marginBottom: '6px', display: 'block' }}>
                    🎨 Solid Colors
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {commonColors.filter(c => !c.isTransparent).map(c => (
                      <button
                        key={c.hex}
                        type="button"
                        onClick={() => setFormData({ ...formData, colorHex: c.hex, colorName: c.name })}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: formData.colorHex === c.hex ? '2px solid #3b82f6' : '1px solid #d1d5db',
                          backgroundColor: formData.colorHex === c.hex ? '#eff6ff' : '#ffffff',
                          cursor: 'pointer',
                        }}
                      >
                        <ColorPreview colorHex={c.hex} size={20} />
                        <span style={{ fontSize: '13px', color: '#374151' }}>{c.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Transparent Colors */}
                <div>
                  <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: 500, marginBottom: '6px', display: 'block' }}>
                    🔍 Transparent Colors
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {commonColors.filter(c => c.isTransparent).map(c => (
                      <button
                        key={c.hex}
                        type="button"
                        onClick={() => setFormData({ ...formData, colorHex: c.hex, colorName: c.name })}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          border: formData.colorHex === c.hex ? '2px solid #3b82f6' : '1px solid #d1d5db',
                          backgroundColor: formData.colorHex === c.hex ? '#eff6ff' : '#ffffff',
                          cursor: 'pointer',
                        }}
                      >
                        <ColorPreview colorHex={c.hex} size={20} />
                        <span style={{ fontSize: '13px', color: '#374151' }}>{c.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Step 4: Number of Spools */}
              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>4️⃣ Jumlah Spool (1 spool = 1kg)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, stockCount: Math.max(1, formData.stockCount - 1) })}
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      fontSize: '20px',
                      cursor: 'pointer',
                    }}
                  >
                    −
                  </button>
                  <input
                    type="number"
                    min="1"
                    value={formData.stockCount}
                    onChange={e => setFormData({ ...formData, stockCount: parseInt(e.target.value) || 1 })}
                    style={{
                      width: '80px',
                      padding: '12px',
                      textAlign: 'center',
                      fontSize: '18px',
                      fontWeight: 600,
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, stockCount: formData.stockCount + 1 })}
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      backgroundColor: '#ffffff',
                      fontSize: '20px',
                      cursor: 'pointer',
                    }}
                  >
                    +
                  </button>
                  <span style={{ fontSize: '14px', color: '#6b7280' }}>spool = {formData.stockCount * 1000}g</span>
                </div>
              </div>

              {/* Notes (optional) */}
              <div style={{ marginBottom: '24px' }}>
                <label style={labelStyle}>📝 Catatan (opsional)</label>
                <textarea
                  value={formData.notes}
                  onChange={e => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Catatan tambahan..."
                  rows={2}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </div>

              {/* Preview */}
              <div style={{
                padding: '16px',
                backgroundColor: '#f0f9ff',
                borderRadius: '12px',
                marginBottom: '24px',
                border: '1px solid #bae6fd',
              }}>
                <div style={{ fontSize: '13px', color: '#0369a1', marginBottom: '8px', fontWeight: 500 }}>
                  📋 Preview Filament:
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <ColorPreview colorHex={formData.colorHex} size={36} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '15px', color: '#1f2937' }}>
                      {formData.brand} {formData.materialType} {formData.colorName} {formData.spoolWeight}g
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      {(() => {
                        const preset = filamentPresets[formData.brand]?.[formData.materialType] || defaultPreset;
                        return `Nozzle: ${preset.nozzleTempDefault}°C | Bed: ${preset.bedTempDefault}°C | K: ${preset.kValue}`;
                      })()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={handleCloseModal}
                  style={{
                    padding: '12px 24px',
                    borderRadius: '8px',
                    border: '1px solid #d1d5db',
                    backgroundColor: '#ffffff',
                    color: '#374151',
                    fontSize: '14px',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  Batal
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '12px 32px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: '#22c55e',
                    color: '#ffffff',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  ✓ {editingId ? 'Simpan' : 'Tambah Filament'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
