# Capstone V3: Frontend Architecture

**Version:** 3.0.0  
**Framework:** React + Vite + Tailwind CSS  
**Audience:** Frontend Engineers, Full-Stack Developers  
**Purpose:** Frontend component architecture and state management

---

## 🏗️ Frontend Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Build Tool | **Vite** | Lightning-fast dev server and bundler |
| UI Framework | **React 18** | Component-based UI with hooks |
| Styling | **Tailwind CSS** | Utility-first CSS |
| Canvas | **p5.js or fabric.js** | 2D canvas rendering and interaction |
| State | **React hooks** | useState, useEffect, useContext |
| HTTP Client | **fetch API** (or axios) | API communication |
| Image Processing | **Canvas API** (native) | Client-side image manipulation |

---

## 📁 Project Structure

```
frontend/
├── public/                             # Static assets
│   └── images/
│
├── src/
│   ├── App.jsx                         # Root component
│   ├── main.jsx                        # Entry point
│   ├── index.css                       # Global styles
│   │
│   ├── pages/                          # Page-level components
│   │   ├── Home.jsx                    # Landing page
│   │   ├── CapstoneStudio.jsx          # ⭐ V3 Main canvas editor
│   │   ├── Dashboard.jsx               # Scene gallery
│   │   ├── History.jsx                 # Edit history viewer
│   │   ├── V2Studio.jsx                # Legacy V2 editor
│   │   ├── Generate.jsx                # V1 generation
│   │   ├── Onboarding.jsx              # V1 onboarding
│   │   ├── LinkedIn.jsx                # LinkedIn integration
│   │   └── ResearchLab.jsx             # Research tools
│   │
│   ├── components/                     # Reusable components
│   │   ├── Layout.jsx                  # Header, nav, footer
│   │   ├── ElementFeedback.jsx         # Validation feedback
│   │   ├── BrandRouteRedirect.jsx      # Route guards
│   │   │
│   │   └── v2/                         # V2/V3 shared components
│   │       ├── CanvasRenderer.jsx      # Renders image + overlays
│   │       ├── ToolPanel.jsx           # Segmentation tools
│   │       ├── HistoryPanel.jsx        # Edit timeline
│   │       ├── SettingsModal.jsx       # Accuracy presets
│   │       ├── UploadModal.jsx         # Image upload
│   │       └── MaskOverlay.jsx         # Display segmentation masks
│   │
│   ├── services/                       # API clients
│   │   ├── v3_client.ts                # ⭐ V3 API wrapper
│   │   ├── v2_client.ts                # V2 API wrapper
│   │   └── common.ts                   # Shared utilities
│   │
│   ├── hooks/                          # Custom React hooks
│   │   ├── useScene.ts                 # Scene state management
│   │   ├── useCanvas.ts                # Canvas interaction
│   │   └── useAPI.ts                   # API call wrapper
│   │
│   └── utils/                          # Utility functions
│       ├── coordinates.ts              # Coordinate transformations
│       ├── image.ts                    # Image manipulation
│       └── validation.ts               # Input validation
│
├── package.json                        # Dependencies
├── vite.config.js                      # Vite configuration
├── tailwind.config.js                  # Tailwind configuration
└── tsconfig.json                       # TypeScript configuration
```

---

## 🖼️ CapstoneStudio.jsx (Main V3 Component)

The main editing interface for V3:

```jsx
import React, { useState, useEffect, useRef } from 'react';
import { V3Client } from '../services/v3_client';
import CanvasRenderer from '../components/v2/CanvasRenderer';
import ToolPanel from '../components/v2/ToolPanel';
import HistoryPanel from '../components/v2/HistoryPanel';
import SettingsModal from '../components/v2/SettingsModal';
import UploadModal from '../components/v2/UploadModal';

/**
 * V3 Capstone Studio - Main editing interface
 *
 * STATE:
 * - scene: SceneDocument (all objects, edits, versions)
 * - canvas_image: URL to current composite image
 * - selected_object: Currently selected object for editing
 * - masks_visible: Whether to show segmentation overlays
 * - history_visible: Whether to show edit history
 * - settings_visible: Whether to show accuracy presets
 * - loading: Shows spinner during API calls
 * - error: Shows error banner if API fails
 *
 * USER FLOWS:
 * 1. Upload → POST /api/v3/scenes/upload → Load scene
 * 2. Click object → POST /api/v3/scenes/{id}/segment-click → SAM2
 * 3. Remove object → POST /api/v3/scenes/{id}/remove-object → LaMa inpaint
 * 4. View history → GET /api/v3/scenes/{id}/history
 */
export default function CapstoneStudio() {
  // State
  const [scene, setScene] = useState(null);
  const [sceneId, setSceneId] = useState(null);
  const [canvasImage, setCanvasImage] = useState(null);
  const [selectedObject, setSelectedObject] = useState(null);
  const [masksVisible, setMasksVisible] = useState(false);
  const [segmentationMasks, setSegmentationMasks] = useState({});
  const [historyVisible, setHistoryVisible] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [accuracyPreset, setAccuracyPreset] = useState('balanced');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const canvasRef = useRef(null);

  const apiClient = new V3Client('http://localhost:8000/api/v3');

  // Initialize
  useEffect(() => {
    loadCapabilities();
  }, []);

  // Load available models
  const loadCapabilities = async () => {
    try {
      const caps = await apiClient.getCapabilities();
      if (!caps.sam2.ready || !caps.lama.ready) {
        setError('Warning: Some ML models are not available. Mock fallbacks enabled.');
      }
    } catch (err) {
      setError(`Failed to check capabilities: ${err.message}`);
    }
  };

  // WORKFLOW 1: Upload image
  const handleUpload = async (file, title) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      formData.append('owner_user_id', 'local-user');

      const response = await fetch('http://localhost:8000/api/v3/scenes/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.detail);

      // Fetch full scene document
      const sceneDoc = await apiClient.getScene(result.scene_id);
      setSceneId(result.scene_id);
      setScene(sceneDoc);
      setCanvasImage(result.image_url);
      setSegmentationMasks({});
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // WORKFLOW 2: Click to segment
  const handleCanvasClick = async (x, y) => {
    if (!sceneId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.segmentClick(sceneId, {
        click_x: x,
        click_y: y,
        label: 'object',
        confidence: 1.0,
        register_object: true,
        tuning: accuracyPreset === 'balanced' 
          ? undefined 
          : { ...getAccuracyPreset(accuracyPreset).segmentation },
      });

      // Store mask for visualization
      setSegmentationMasks(prev => ({
        ...prev,
        [response.object_id]: {
          mask_url: response.mask_url,
          bbox: response.bbox,
        }
      }));

      setSelectedObject(response.object_id);
      setMasksVisible(true);

      // Refresh scene state
      const updated = await apiClient.getScene(sceneId);
      setScene(updated);
    } catch (err) {
      setError(`Segmentation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // WORKFLOW 3: Remove object
  const handleRemoveObject = async (objectId) => {
    if (!sceneId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.removeObject(sceneId, {
        object_id: objectId,
        record_event: true,
        tuning: getAccuracyPreset(accuracyPreset).inpainting,
      });

      // Update canvas image
      setCanvasImage(response.new_canvas_image_url);
      setSegmentationMasks({});
      setSelectedObject(null);
      setMasksVisible(false);

      // Refresh scene state
      const updated = await apiClient.getScene(sceneId);
      setScene(updated);
    } catch (err) {
      setError(`Removal failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Get accuracy presets
  const getAccuracyPreset = (preset) => {
    const presets = {
      balanced: {
        segmentation: { dilate_px: 0, erode_px: 0 },
        inpainting: { mask_dilate_px: 4, enable_refinement: false }
      },
      tight_edges: {
        segmentation: { dilate_px: 0, erode_px: 1 },
        inpainting: { mask_dilate_px: 4, enable_refinement: false }
      },
      hq: {
        segmentation: { dilate_px: 2, erode_px: 0 },
        inpainting: { mask_dilate_px: 3, enable_refinement: true }
      }
    };
    return presets[preset] || presets.balanced;
  };

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Left Sidebar - Tools */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
        <h2 className="text-xl font-bold text-white mb-4">Tools</h2>

        {/* Upload */}
        <button
          onClick={() => setSettingsVisible(true)}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded mb-4"
          disabled={loading}
        >
          {sceneId ? 'Change Image' : 'Upload Image'}
        </button>

        {/* Accuracy Presets */}
        {sceneId && (
          <>
            <div className="mb-4">
              <label className="text-gray-300 text-sm block mb-2">Accuracy Preset</label>
              <select
                value={accuracyPreset}
                onChange={(e) => setAccuracyPreset(e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 text-white rounded"
              >
                <option value="balanced">Balanced</option>
                <option value="tight_edges">Tight Edges</option>
                <option value="hq">High Quality</option>
              </select>
            </div>

            {/* Segmentation Tool */}
            <div className="mb-4">
              <h3 className="text-white font-semibold mb-2">Segmentation</h3>
              <p className="text-gray-300 text-sm mb-2">
                Click on an object in the canvas to segment it.
              </p>
              <button
                onClick={() => setMasksVisible(!masksVisible)}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded"
              >
                {masksVisible ? 'Hide Masks' : 'Show Masks'}
              </button>
            </div>

            {/* Remove Object */}
            {selectedObject && (
              <div className="mb-4">
                <h3 className="text-white font-semibold mb-2">Selected Object</h3>
                <p className="text-gray-300 text-sm mb-2">
                  ID: {selectedObject.slice(0, 12)}...
                </p>
                <button
                  onClick={() => handleRemoveObject(selectedObject)}
                  className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
                  disabled={loading}
                >
                  Remove Object
                </button>
              </div>
            )}

            {/* History */}
            <button
              onClick={() => setHistoryVisible(!historyVisible)}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
            >
              {historyVisible ? 'Hide History' : 'Show History'}
            </button>
          </>
        )}

        {/* Status */}
        {loading && <p className="text-yellow-400 mt-4">Processing...</p>}
        {error && <p className="text-red-400 mt-4 text-sm">{error}</p>}
      </div>

      {/* Center - Canvas */}
      <div className="flex-1 flex flex-col bg-gray-900">
        <div className="flex-1 relative overflow-auto p-4">
          {canvasImage ? (
            <CanvasRenderer
              imageUrl={canvasImage}
              masks={masksVisible ? segmentationMasks : {}}
              selectedObjectId={selectedObject}
              onClick={handleCanvasClick}
              ref={canvasRef}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-400 text-lg">No image loaded. Upload an image to start.</p>
            </div>
          )}
        </div>
      </div>

      {/* Right Sidebar - History */}
      {historyVisible && scene && (
        <HistoryPanel
          sceneId={sceneId}
          events={scene.edit_events}
          onClose={() => setHistoryVisible(false)}
        />
      )}

      {/* Modals */}
      {settingsVisible && (
        <UploadModal
          onUpload={handleUpload}
          onClose={() => setSettingsVisible(false)}
          loading={loading}
        />
      )}
    </div>
  );
}
```

---

## 🎛️ Key Sub-Components

### CanvasRenderer.jsx
Renders the image and interactive overlays:

```jsx
import React, { useRef, useEffect } from 'react';

/**
 * Displays image with optional mask overlays and click detection.
 *
 * PROPS:
 * - imageUrl: URL to display
 * - masks: { object_id: { mask_url, bbox } }
 * - selectedObjectId: Highlight this object
 * - onClick: Callback (x, y) normalized 0-1
 */
const CanvasRenderer = React.forwardRef(
  ({ imageUrl, masks, selectedObjectId, onClick }, ref) => {
    const containerRef = useRef(null);
    const imgRef = useRef(new Image());

    useEffect(() => {
      const img = new Image();
      img.src = imageUrl;
      img.onload = () => {
        imgRef.current = img;
        redraw();
      };
    }, [imageUrl]);

    const redraw = () => {
      const canvas = document.getElementById('canvas');
      if (!canvas || !imgRef.current) return;

      const ctx = canvas.getContext('2d');
      const w = imgRef.current.width;
      const h = imgRef.current.height;

      // Scale canvas to fit container
      canvas.width = w;
      canvas.height = h;

      // Draw image
      ctx.drawImage(imgRef.current, 0, 0, w, h);

      // Draw masks
      for (const [objId, { mask_url, bbox }] of Object.entries(masks || {})) {
        const maskImg = new Image();
        maskImg.src = mask_url;
        maskImg.onload = () => {
          ctx.globalAlpha = 0.3;
          ctx.fillStyle = objId === selectedObjectId ? '#00FF00' : '#FF00FF';
          ctx.fillRect(bbox.x, bbox.y, bbox.w, bbox.h);
          ctx.globalAlpha = 1.0;
        };
      }
    };

    const handleCanvasClick = (e) => {
      const canvas = e.currentTarget;
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      onClick?.(x, y);
    };

    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center bg-gray-800">
        <canvas
          id="canvas"
          ref={ref}
          onClick={handleCanvasClick}
          className="max-w-full max-h-full cursor-crosshair"
        />
      </div>
    );
  }
);

export default CanvasRenderer;
```

### HistoryPanel.jsx
Timeline view of edits:

```jsx
import React, { useEffect, useState } from 'react';
import { V3Client } from '../services/v3_client';

const HistoryPanel = ({ sceneId, events, onClose }) => {
  const apiClient = new V3Client('http://localhost:8000/api/v3');

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 p-4 overflow-y-auto">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-white">Edit History</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          ✕
        </button>
      </div>

      <div className="space-y-2">
        {(events || []).map((event, idx) => (
          <div key={event.event_id} className="p-3 bg-gray-700 rounded text-sm">
            <p className="text-gray-300 font-semibold">
              {idx + 1}. {event.event_type}
            </p>
            <p className="text-gray-400 text-xs">
              {new Date(event.created_at).toLocaleString()}
            </p>
            <p className="text-gray-300 mt-1">
              Affected: {event.affected_object_ids.length} object(s)
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HistoryPanel;
```

---

## 🌐 V3 API Client

**File:** `src/services/v3_client.ts`

TypeScript wrapper around V3 endpoints:

```typescript
export class V3Client {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async getCapabilities() {
    return this.get('/capabilities');
  }

  async createScene(req: CreateSceneRequest): Promise<SceneDocument> {
    return this.post('/scenes', req);
  }

  async getScene(sceneId: string): Promise<SceneDocument> {
    return this.get(`/scenes/${sceneId}`);
  }

  async segmentClick(sceneId: string, req: SegmentClickRequest) {
    return this.post(`/scenes/${sceneId}/segment-click`, req);
  }

  async removeObject(sceneId: string, req: RemoveObjectRequest) {
    return this.post(`/scenes/${sceneId}/remove-object`, req);
  }

  async getHistory(sceneId: string) {
    return this.get(`/scenes/${sceneId}/history`);
  }

  private async get(endpoint: string) {
    const response = await fetch(`${this.baseURL}${endpoint}`);
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }

  private async post(endpoint: string, body: any) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  }
}
```

---

## 🎨 Styling with Tailwind

V3 Studio uses dark theme with accent colors:

```css
/* globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Color scheme */
:root {
  --bg-primary: #111827;    /* gray-900 */
  --bg-secondary: #1f2937;  /* gray-800 */
  --bg-tertiary: #374151;   /* gray-700 */
  --text-primary: #ffffff;
  --text-secondary: #d1d5db;
  --accent-primary: #3b82f6;    /* blue-500 */
  --accent-danger: #ef4444;     /* red-500 */
  --accent-success: #10b981;    /* green-500 */
}

.studio-container {
  @apply flex h-screen bg-gray-900;
}

.studio-panel {
  @apply bg-gray-800 border border-gray-700 rounded-lg p-4 shadow-lg;
}

.studio-button-primary {
  @apply px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold;
}

.studio-button-danger {
  @apply px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-semibold;
}

.studio-button-disabled {
  @apply opacity-50 cursor-not-allowed;
}
```

---

## 🔄 State Management Pattern

V3 uses React hooks for state (no Redux):

```jsx
// Simplified pattern:
const [state, setState] = useState(initialValue);

// Effects for side-effects:
useEffect(() => {
  // Run when dependencies change
  loadData();
}, [dependency]);

// Custom hooks for reusable logic:
function useScene(sceneId) {
  const [scene, setScene] = useState(null);
  useEffect(() => {
    apiClient.getScene(sceneId).then(setScene);
  }, [sceneId]);
  return scene;
}
```

---

## 📊 User Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPSTONE STUDIO V3                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌──────────────┬─────────────────────────────┬────────────────┐ │
│ │   TOOLS      │                             │    HISTORY     │ │
│ │              │      CANVAS EDITOR          │                │ │
│ │ • Upload     │                             │ • Timeline     │ │
│ │ • Presets    │    [IMAGE WITH MASKS]       │ • Edit Events  │ │
│ │ • Segment    │                             │ • Restore      │ │
│ │ • Remove     │                             │                │ │
│ │ • History    │                             │                │ │
│ │              │                             │                │ │
│ └──────────────┴─────────────────────────────┴────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Development Workflow

**Start dev server:**
```bash
cd frontend
npm run dev  # Vite dev server at localhost:5173
```

**Build for production:**
```bash
npm run build  # Creates optimized dist/ folder
npm run preview  # Test build locally
```

**Code structure:**
- Hot module reloading (HMR) enabled for fast development
- TypeScript for type safety
- Tailwind for utility-first CSS
- ESLint for code quality

---

## 🧪 Frontend Testing Strategy

```bash
# Unit tests (Vitest)
npm run test

# E2E tests (Playwright)
npm run test:e2e

# Coverage report
npm run coverage
```

---

## 📝 Summary

V3 Frontend:
- **React + Vite** for modern, fast development
- **Canvas-based** for image manipulation UI
- **Tailwind** for dark theme
- **Hooks** for state management
- **TypeScript** for type safety
- **API client** for clean backend communication

---

**Next:** Read [06_INTEGRATION_GUIDE_V3.md](./06_INTEGRATION_GUIDE_V3.md) for complete system integration.
