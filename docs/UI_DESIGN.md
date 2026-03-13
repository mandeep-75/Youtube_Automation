# YouTube Automation Pipeline - UI/UX Design Document

## Project Overview

**Project Name:** YouTube Automation Pipeline Dashboard  
**Project Type:** Web Application (React Frontend + FastAPI Backend)  
**Core Functionality:** A professional video processing dashboard that enables users to upload videos, configure the 8-step AI-powered video processing pipeline, monitor progress in real-time, and manage batch processing jobs.  
**Target Users:** Video content creators, social media managers, and video production teams who need to automate video narration and subtitle generation.

---

## 1. UI/UX Design Concept

### 1.1 Layout Structure

The application uses a **three-panel layout** optimized for video production workflows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HEADER (64px) - Logo, Navigation Tabs, Theme Toggle, Settings            │
├─────────────────────────────────────────────────────────────────────────────┤
│                    │                                  │                       │
│   SIDEBAR          │   MAIN CONTENT                 │   RIGHT PANEL        │
│   (280px)          │   (flex-1)                      │   (320px)            │
│                    │                                  │                       │
│   - Upload Zone    │   - Pipeline Visualization      │   - Job Queue        │
│   - Video Library  │   - Video Preview               │   - Batch Progress    │
│   - Quick Actions  │   - Configuration Panels        │   - History          │
│                    │                                  │                       │
└────────────────────┴──────────────────────────────────┴───────────────────────┘
```

**Responsive Breakpoints:**
- **Desktop:** 1280px+ (full three-panel layout)
- **Tablet:** 768px - 1279px (collapsible sidebar, stacked panels)
- **Mobile:** < 768px (single column, tabbed navigation)

### 1.2 Visual Design System

#### Color Palette

**Dark Mode (Primary):**
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#0D0D0F` | Main background |
| `--bg-secondary` | `#161619` | Cards, panels |
| `--bg-tertiary` | `#1E1E22` | Input fields, hover states |
| `--border` | `#2A2A2E` | Dividers, borders |
| `--text-primary` | `#F4F4F5` | Headings, important text |
| `--text-secondary` | `#A1A1AA` | Body text, labels |
| `--text-muted` | `#71717A` | Placeholders, hints |
| `--accent-primary` | `#6366F1` | Primary actions, links |
| `--accent-hover` | `#818CF8` | Hover states |
| `--success` | `#22C55E` | Completed steps |
| `--warning` | `#F59E0B` | In progress |
| `--error` | `#EF4444` | Failed steps |
| `--info` | `#3B82F6` | Information |

**Light Mode:**
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#FAFAFA` | Main background |
| `--bg-secondary` | `#FFFFFF` | Cards, panels |
| `--bg-tertiary` | `#F4F4F5` | Input fields |
| `--border` | `#E4E4E7` | Dividers |
| `--text-primary` | `#18181B` | Headings |
| `--text-secondary` | `#52525B` | Body text |

#### Typography

| Element | Font | Size | Weight | Line Height |
|---------|------|------|--------|-------------|
| App Title | Inter | 20px | 700 | 1.2 |
| Section Headers | Inter | 16px | 600 | 1.3 |
| Body Text | Inter | 14px | 400 | 1.5 |
| Labels | Inter | 12px | 500 | 1.4 |
| Code/Paths | JetBrains Mono | 13px | 400 | 1.5 |
| Pipeline Steps | Inter | 13px | 600 | 1.2 |

#### Spacing System (8px Base)

- `--space-1`: 4px
- `--space-2`: 8px
- `--space-3`: 12px
- `--space-4`: 16px
- `--space-5`: 20px
- `--space-6`: 24px
- `--space-8`: 32px
- `--space-10`: 40px
- `--space-12`: 48px

#### Visual Effects

- **Card shadows:** `0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)`
- **Elevated shadows:** `0 10px 15px -3px rgba(0, 0, 0, 0.4)`
- **Border radius:** 8px (cards), 6px (buttons), 4px (inputs)
- **Transitions:** 200ms ease for interactions, 300ms ease for panels

### 1.3 Component States

#### Buttons

| State | Background | Text | Border | Transform |
|-------|------------|------|--------|-----------|
| Default | `--accent-primary` | white | none | none |
| Hover | `--accent-hover` | white | none | translateY(-1px) |
| Active | `--accent-primary` (darker) | white | none | translateY(0) |
| Disabled | `--bg-tertiary` | `--text-muted` | `--border` | none |
| Loading | `--accent-primary` | transparent | none | spinner animation |

#### Pipeline Step Indicators

| Status | Icon | Color | Animation |
|--------|------|-------|-----------|
| Pending | Circle outline | `--text-muted` | none |
| In Progress | Spinner | `--warning` | pulse 1.5s infinite |
| Completed | Checkmark | `--success` | scale 0.3s |
| Failed | X mark | `--error` | shake 0.3s |
| Skipped | Slash | `--text-muted` | none |

---

## 2. Page Structure

### 2.1 Main Dashboard View

The primary interface consists of:

#### Left Sidebar (280px)

```
┌─────────────────────────────┐
│  📤 UPLOAD                  │
│  ┌─────────────────────┐    │
│  │                     │    │
│  │   Drop videos here  │    │
│  │   or click to      │    │
│  │   browse            │    │
│  │                     │    │
│  └─────────────────────┘    │
│  Supported: MP4, MOV, AVI   │
│                             │
│  📁 VIDEO LIBRARY           │
│  ┌─────────────────────┐    │
│  │ 🔍 Search...        │    │
│  ├─────────────────────┤    │
│  │ 📹 video_001.mp4    │    │
│  │    2:34 • 15MB      │    │
│  ├─────────────────────┤    │
│  │ 📹 video_002.mp4    │    │
│  │    1:15 • 8MB       │    │
│  ├─────────────────────┤    │
│  │ 📹 funny_cat.mp4   │    │
│  │    0:45 • 5MB       │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

#### Main Content Area

```
┌─────────────────────────────────────────────────────────────────┐
│  PIPELINE STATUS                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ① Extract    ② Vision    ③ Transcribe   ④ Script Gen   │  │
│  │     ●○○○○      ●○○○○       ●○○○○          ●○○○○         │  │
│  │                                                            │  │
│  │  ⑤ TTS       ⑥ Merge     ⑦ Subtitle     ⑧ Burn Subs    │  │
│  │     ○○○○○      ○○○○○       ○○○○○          ○○○○○         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  VIDEO PREVIEW                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                                                        │    │
│  │                   [ Video Player ]                    │    │
│  │                                                        │    │
│  │                   ▶️ 00:00 / 02:34                    │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  CURRENT JOB DETAILS                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Step: Frame Extraction              Progress: 45/120   │    │
│  │ ████████████░░░░░░░░░░░░░░░░░░░░░░░  37%                │    │
│  │ Started: 2:34 PM • ETA: ~3 minutes                     │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

#### Right Panel (320px)

```
┌─────────────────────────────┐
│  ⚙️ JOB QUEUE               │
│  ┌─────────────────────┐    │
│  │ ▶ video_001.mp4     │    │
│  │   Processing...     │    │
│  ├─────────────────────┤    │
│  │ ⏸ video_002.mp4     │    │
│  │   Pending           │    │
│  ├─────────────────────┤    │
│  │ ⏸ video_003.mp4    │    │
│  │   Pending           │    │
│  └─────────────────────┘    │
│                             │
│  [+ Add to Queue ]         │
│                             │
│  📊 STATISTICS             │
│  ┌─────────────────────┐    │
│  │ Processed Today: 12 │    │
│  │ Success Rate: 92%   │    │
│  │ Avg. Time: 4:32     │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

### 2.2 Configuration Panel (Slide-out Drawer)

Accessed via gear icon or clicking a step in the pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ CONFIGURATION                              [X Close]       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  OLLAMA SETTINGS                                        │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Ollama URL:  [ http://localhost:11434        ] [Test]  │   │
│  │  Status: ● Connected                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 1: FRAME EXTRACTION                               │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Frame Interval (seconds):  [ 1.0  ]                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 2: VISION MODEL                                   │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Model:  [ qwen3-vl:2b              ▼]                 │   │
│  │  Prompt Template:                                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ [Expandable textarea with default prompt]       │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 3: WHISPER TRANSCRIPTION                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Model:     [ base              ▼]                      │   │
│  │  Language:  [ Auto-detect       ▼]                      │   │
│  │  Beam Size:  [ 5  ]   Compute: [ int8  ▼]               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 4: LLM SCRIPT GENERATION                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Model:     [ jaahas/qwen3.5-uncensored:9b ▼]          │   │
│  │  Words/Second:  [ 3.0 ]                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 5: TEXT-TO-SPEECH                                 │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Reference Audio:  [ Choose File...            ] [▶]    │   │
│  │  ┌─────────────────────────────────────────────────┐     │   │
│  │  │ Audio waveform preview                        │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  │                                                          │   │
│  │  Exaggeration:   [═══════●═══] 0.6                       │   │
│  │  Temperature:    [═●═════════] 0.05                      │   │
│  │  CFG Weight:     [══════●════] 0.5                       │   │
│  │  Repetition:     [══════●════] 1.2                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 6: AUDIO MERGE                                    │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  [✓] Mix original audio with TTS                       │   │
│  │  Original Volume:  [══════●═══════] 0.4                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  STEP 7-8: SUBTITLES                                    │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Font:        [ Anton ▼]     Size: [ 120 ]              │   │
│  │  Font Color:  [#FFFFFF  ]  Highlight: [#00FFAA]        │   │
│  │  Outline:     [#000000  ]  Width: [ 1.0 ]              │   │
│  │  Position:    [ Center  ▼]                              │   │
│  │  Max Words/Line: [ 3 ]                                 │   │
│  │  [✓] Bold   [ ] Italic                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                    [ Reset to Defaults ]  [ Save Configuration ]│
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Video Details Modal

When clicking on a processed video:

```
┌─────────────────────────────────────────────────────────────────┐
│  📹 video_001.mp4                                   [X Close]  │
│                                                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │                         │  │ DETAILS                    │   │
│  │   [ Video Player ]      │  │ ─────────────────────────  │   │
│  │                         │  │ Duration: 2:34             │   │
│  │                         │  │ Size: 15 MB                │   │
│  │         ▶️             │  │ Uploaded: Jan 15, 2026     │   │
│  └─────────────────────────┘  │ Processed: Jan 15, 2026    │   │
│                               │ Status: ✓ Completed        │   │
│  [▶ Play Original]            └─────────────────────────────┘   │
│  [▶ Play Processed]                                          │
│                                                                 │
│  PIPELINE RESULTS                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Frame Extraction: ✓ 120 frames extracted               │   │
│  │ Vision Descriptions: ✓ Generated (1.2KB)                │   │
│  │ Audio Transcription: ✓ 3:42 of audio transcribed        │   │
│  │ Narration Script: ✓ 450 words generated                 │   │
│  │ TTS Generation: ✓ voice.wav (3:42)                      │   │
│  │ Audio Merge: ✓ video_with_tts.mp4                       │   │
│  │ Subtitle Transcription: ✓ subtitles.srt                │   │
│  │ Final Render: ✓ final_video.mp4                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  NARRATION SCRIPT                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │ In this video, we see a man walking down a busy street │   │
│  │ carrying shopping bags. He appears to be heading home   │   │
│  │ after a day of shopping. The camera follows him as he   │   │
│  │ navigates through the crowd...                          │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [📥 Download All]  [📤 Upload to YouTube]  [🗑 Delete]       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Structure

### 3.1 Component Hierarchy

```
App
├── ThemeProvider (dark/light mode)
├── Header
│   ├── Logo
│   ├── Navigation (Dashboard, Queue, History, Settings)
│   ├── ThemeToggle
│   └── NotificationBell
├── MainLayout
│   ├── Sidebar
│   │   ├── UploadZone
│   │   │   ├── FileDropzone
│   │   │   └── UploadButton
│   │   ├── VideoLibrary
│   │   │   ├── SearchInput
│   │   │   └── VideoList
│   │   │       └── VideoItem
│   │   └── QuickActions
│   ├── ContentArea
│   │   ├── PipelineDashboard
│   │   │   ├── PipelineSteps (8 steps)
│   │   │   │   └── StepIndicator
│   │   │   ├── VideoPreview
│   │   │   │   ├── VideoPlayer
│   │   │   │   └── PlaybackControls
│   │   │   └── JobProgress
│   │   │       ├── ProgressBar
│   │   │       ├── StepDetails
│   │   │       └── ETAEstimate
│   │   ├── VideoDetails
│   │   │   ├── VideoPlayer
│   │   │   ├── PipelineResults
│   │   │   └── ScriptPreview
│   │   └── QueueView
│   │       ├── QueueList
│   │       │   └── QueueItem
│   │       └── QueueControls
│   └── RightPanel
│       ├── JobQueue
│       │   └── QueueItem (compact)
│       └── Statistics
├── ConfigurationDrawer
│   ├── OllamaConfig
│   ├── StepConfig (1-8)
│   │   ├── FrameExtractionSettings
│   │   ├── VisionModelSettings
│   │   ├── WhisperSettings
│   │   ├── LLMSettings
│   │   ├── TTSSettings
│   │   ├── AudioMergeSettings
│   │   └── SubtitleSettings
│   └── ConfigActions
└── Modals
    ├── VideoDetailsModal
    ├── UploadModal
    └── ConfirmDialog
```

### 3.2 Core Components

#### StepIndicator
```typescript
interface StepIndicatorProps {
  stepNumber: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  progress?: number; // 0-100
  description?: string;
  isActive?: boolean;
  onClick?: () => void;
}
```

#### VideoPlayer
```typescript
interface VideoPlayerProps {
  src: string;
  type: 'original' | 'processed' | 'preview';
  controls?: boolean;
  autoPlay?: boolean;
  onTimeUpdate?: (currentTime: number) => void;
}
```

#### ConfigurationPanel
```typescript
interface ConfigSectionProps {
  stepName: string;
  icon: string;
  fields: ConfigField[];
  isExpanded?: boolean;
  onToggle?: () => void;
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'slider' | 'toggle' | 'file';
  value: any;
  options?: SelectOption[];
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}
```

#### JobQueueItem
```typescript
interface JobQueueItem {
  id: string;
  filename: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'paused';
  progress: number;
  currentStep?: number;
  error?: string;
  addedAt: Date;
  startedAt?: Date;
  completedAt?: Date;
}
```

---

## 4. API Endpoint Suggestions

### 4.1 Backend Architecture

The FastAPI backend should expose these endpoints:

#### Jobs API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Upload video and create new job |
| `GET` | `/api/jobs` | List all jobs (with filters) |
| `GET` | `/api/jobs/{job_id}` | Get job details |
| `DELETE` | `/api/jobs/{job_id}` | Delete job and files |
| `POST` | `/api/jobs/{job_id}/start` | Start processing |
| `POST` | `/api/jobs/{job_id}/pause` | Pause processing |
| `POST` | `/api/jobs/{job_id}/resume` | Resume processing |
| `GET` | `/api/jobs/{job_id}/stream` | SSE for real-time progress |

#### Videos API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/videos` | List all videos in library |
| `GET` | `/api/videos/{video_id}` | Get video metadata |
| `GET` | `/api/videos/{video_id}/download` | Download processed video |
| `GET` | `/api/videos/{video_id}/preview` | Stream video for preview |

#### Configuration API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config` | Get current configuration |
| `PUT` | `/api/config` | Update configuration |
| `POST` | `/api/config/test-ollama` | Test Ollama connection |
| `GET` | `/api/config/models` | List available Ollama models |
| `POST` | `/api/config/test-tts` | Test TTS with sample |

#### System API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/system/stats` | Get processing statistics |
| `GET` | `/api/system/health` | Health check |
| `GET` | `/api/system/logs` | Get application logs |

### 4.2 API Request/Response Examples

#### POST /api/jobs
```json
// Request
{
  "file": "<multipart file>",
  "options": {
    "skipSteps": [],
    "customConfig": {}
  }
}

// Response
{
  "id": "job_abc123",
  "filename": "video_001.mp4",
  "status": "queued",
  "createdAt": "2026-01-15T14:30:00Z",
  "progress": 0,
  "currentStep": null
}
```

#### GET /api/jobs/{job_id}/stream (SSE)
```typescript
// Server-Sent Events format
data: {"step": 1, "status": "running", "progress": 45, "message": "Extracting frame 45/120"}
data: {"step": 1, "status": "completed", "progress": 100, "message": "120 frames extracted"}
data: {"step": 2, "status": "running", "progress": 0, "message": "Starting vision analysis..."}
```

---

## 5. Implementation Guidance

### 5.1 Tech Stack Recommendation

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | Type safety, component reusability |
| State | Zustand | Lightweight, minimal boilerplate |
| Styling | Tailwind CSS | Rapid development, dark mode support |
| Video Player | Video.js | Professional, accessible |
| Icons | Lucide React | Clean, consistent iconography |
| HTTP Client | Axios | Interceptors, error handling |
| Backend | FastAPI | Python ecosystem, async support |
| Database | SQLite (SQLAlchemy) | Simple, file-based storage |
| File Storage | Local filesystem | Works with existing pipeline |

### 5.2 Project Structure

```
youtube-automation-ui/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Slider.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── RightPanel.tsx
│   │   ├── pipeline/
│   │   │   ├── PipelineSteps.tsx
│   │   │   ├── StepIndicator.tsx
│   │   │   └── JobProgress.tsx
│   │   ├── video/
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── VideoLibrary.tsx
│   │   │   └── UploadZone.tsx
│   │   ├── config/
│   │   │   ├── ConfigurationDrawer.tsx
│   │   │   └── ConfigSections.tsx
│   │   └── queue/
│   │       ├── JobQueue.tsx
│   │       └── QueueItem.tsx
│   ├── hooks/
│   │   ├── useJobs.ts
│   │   ├── useConfig.ts
│   │   ├── useTheme.ts
│   │   └── use SSE.ts
│   ├── stores/
│   │   ├── jobStore.ts
│   │   ├── configStore.ts
│   │   └── uiStore.ts
│   ├── services/
│   │   ├── api.ts
│   │   └── sse.ts
│   ├── types/
│   │   └── index.ts
│   ├── styles/
│   │   └── globals.css
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts

youtube-automation-api/
├── main.py
├── api/
│   ├── routes/
│   │   ├── jobs.py
│   │   ├── videos.py
│   │   ├── config.py
│   │   └── system.py
│   └── dependencies.py
├── core/
│   ├── config.py (copied from main repo)
│   ├── pipeline.py (imported from main repo)
│   └── database.py
├── services/
│   ├── pipeline_runner.py
│   └── file_manager.py
└── requirements.txt
```

### 5.3 Real-time Progress Implementation

Using Server-Sent Events (SSE) for real-time pipeline updates:

```python
# Backend (FastAPI)
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

@app.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    async def event_generator():
        while True:
            # Check job status from database/queue
            job = get_job(job_id)
            
            if job:
                yield f"data: {json.dumps(job.to_dict())}\n\n"
                
                if job.status in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

```typescript
// Frontend (React)
import { useEffect, useState } from 'react';

function useJobStream(jobId: string) {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);
    };
    
    eventSource.onerror = () => {
      eventSource.close();
    };
    
    return () => eventSource.close();
  }, [jobId]);
  
  return progress;
}
```

### 5.4 Theme Implementation

```typescript
// src/styles/globals.css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #0D0D0F;
  --bg-secondary: #161619;
  --bg-tertiary: #1E1E22;
  --border: #2A2A2E;
  --text-primary: #F4F4F5;
  --text-secondary: #A1A1AA;
  --text-muted: #71717A;
  --accent-primary: #6366F1;
  --accent-hover: #818CF8;
  --success: #22C55E;
  --warning: #F59E0B;
  --error: #EF4444;
  --info: #3B82F6;
}

[data-theme="light"] {
  --bg-primary: #FAFAFA;
  --bg-secondary: #FFFFFF;
  --bg-tertiary: #F4F4F5;
  --border: #E4E4E7;
  --text-primary: #18181B;
  --text-secondary: #52525B;
  --text-muted: #A1A1AA;
}

* {
  transition: background-color 0.2s ease, border-color 0.2s ease;
}
```

### 5.5 Video Player Implementation

```typescript
// Using Video.js for professional playback
import VideoPlayer from './components/video/VideoPlayer';

<VideoPlayer
  src={videoUrl}
  type="processed"
  onTimeUpdate={(time) => setCurrentTime(time)}
  hotkeys={{
    space: 'play/pause',
    arrowLeft: 'seek-5',
    arrowRight: 'seek+5',
    m: 'mute'
  }}
/>
```

---

## 6. Acceptance Criteria

### Visual Checkpoints

- [ ] Dark mode displays with correct color tokens
- [ ] Light mode toggle works instantly
- [ ] Pipeline step indicators animate on status change
- [ ] Video player loads and plays smoothly
- [ ] Upload dropzone shows visual feedback on drag
- [ ] Configuration sliders update values in real-time
- [ ] Job queue shows accurate status indicators
- [ ] Responsive layout works at all breakpoints

### Functional Checkpoints

- [ ] Video upload creates new job in queue
- [ ] Pipeline starts processing when triggered
- [ ] Real-time progress updates via SSE
- [ ] Configuration changes persist to backend
- [ ] Ollama connection test works
- [ ] TTS test plays sample audio
- [ ] Video details show all pipeline outputs
- [ ] Download exports processed video

### Accessibility

- [ ] All interactive elements keyboard accessible
- [ ] Focus states visible on all controls
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Screen reader labels on icons and buttons
- [ ] Reduced motion respects user preference

---

## 7. Implementation Priority

### Phase 1: Core (Week 1)
1. Project setup with React + TypeScript + Vite
2. Layout structure (Header, Sidebar, Content, Right Panel)
3. Basic theming (dark/light mode)
4. Upload zone component

### Phase 2: Pipeline (Week 2)
1. Pipeline visualization component
2. Video player integration
3. Job queue management
4. SSE for real-time updates

### Phase 3: Configuration (Week 3)
1. Configuration drawer
2. All 8 step settings panels
3. Ollama model selection
4. TTS audio preview

### Phase 4: Polish (Week 4)
1. Animations and transitions
2. Accessibility improvements
3. Error handling
4. Performance optimization

---

**Design System Version:** 1.0  
**Last Updated:** March 13, 2026  
**Designer:** UI Designer Agent
