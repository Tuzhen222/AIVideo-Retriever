# Temporal Aggregation Feature - Testing Guide

## Feature Overview
Two temporal aggregation modes for multi-stage search results:

### Mode 1: ID Aggregation (Default)
- **What**: Aggregates results by media ID across all stages
- **How**: If an ID appears in multiple stages, scores are summed
- **Display**: List view with stage contribution badges showing which stages contributed

### Mode 2: Tuple Sequences
- **What**: Finds sequences where frame indices increase across stages in same video
- **How**: Selects combinations (1 result per stage) where:
  - All results from same video
  - Frame indices strictly increasing: stage1_frame < stage2_frame < stage3_frame < ...
- **Display**: Grouped cards showing all frames in sequence with box border

## How to Test

### 1. Setup Multi-Stage Search
1. Open sidebar
2. Click "Add Query Section" to create 2-3 stages
3. Enter different queries per stage, e.g.:
   - Stage 1: "water"
   - Stage 2: "black"
   - Stage 3: "boy"
4. Enable methods (Multimodal, IC, etc.) per stage
5. Click Search

### 2. View Default (ID Aggregation)
- After search completes, click "Temporal Result" button in header
- Default view shows ID aggregation mode
- Check:
  - ✓ Each result shows aggregated score
  - ✓ Stage badges indicate which stages contributed
  - ✓ Individual stage scores displayed in badges

### 3. Toggle to Tuple Mode
- Click toggle button (rightmost in header when Temporal Result selected)
- Button label changes: "ID View" → "Tuple View"
- System re-fetches with tuple mode
- Check:
  - ✓ Sequences displayed in grouped cards
  - ✓ Each sequence shows frames from all stages
  - ✓ Frame indices increase: Frame 1 < Frame 2 < Frame 3
  - ✓ All frames in sequence from same video
  - ✓ Total score shown per sequence

### 4. Switch Back to ID Mode
- Click toggle again to return to ID aggregation
- Verify smooth transition

### 5. Edge Cases to Test
- **No common videos**: If stages return results from different videos, tuple mode should show "No temporal sequences found"
- **Single stage**: Temporal features should not appear (only works with 2+ stages)
- **Empty results**: One or more stages return no results - check graceful handling
- **Large result sets**: 200+ results per stage - verify performance

## Expected Behavior

### ID Mode Display
```
┌─────────────────────────────────────────┐
│ [Thumbnail] ID: 12345   Score: 2.456   │
│              Stages: [Stage 1 (0.85)]  │
│                     [Stage 2 (0.92)]  │
│                     [Stage 3 (0.69)]  │
│              (3 stages)                │
└─────────────────────────────────────────┘
```

### Tuple Mode Display
```
┌─────────────────────────────────────────────────────┐
│ Sequence #1  Video: L01_V001  Frames: 5 → 12 → 25 │
│ Score: 2.456                         3 stages      │
├─────────────────────────────────────────────────────┤
│ ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│ │ Stage 1 │  │ Stage 2 │  │ Stage 3 │             │
│ ├─────────┤  ├─────────┤  ├─────────┤             │
│ │ [Frame] │  │ [Frame] │  │ [Frame] │             │
│ │ Frame: 5│  │ Frame:12│  │ Frame:25│             │
│ │ ID: xxx │  │ ID: yyy │  │ ID: zzz │             │
│ │ 0.85    │  │ 0.92    │  │ 0.69    │             │
│ └─────────┘  └─────────┘  └─────────┘             │
└─────────────────────────────────────────────────────┘
```

## API Changes

### Request
```json
POST /api/search/multistage
{
  "stages": [...],
  "temporal_mode": "id"  // or "tuple"
}
```

### Response
```json
{
  "stages": [...],
  "total_stages": 3,
  "temporal_aggregation": {
    "mode": "id",
    "results": [
      {
        "id": "12345",
        "score": 2.456,
        "contributing_stages": [1, 2, 3],
        "stage_scores": {
          "1": 0.85,
          "2": 0.92,
          "3": 0.69
        },
        "keyframe_path": "/keyframes/...",
        ...
      }
    ],
    "total": 150
  }
}
```

## Troubleshooting

### Toggle not appearing
- Verify you're viewing "Temporal Result" (not a stage)
- Check multi-stage search (2+ stages required)

### No tuples found
- Stages may return results from different videos
- Try queries that target same video content
- Check frame index extraction from keyframe_path

### Performance issues
- Backend limits tuples to 200 max
- ID aggregation should handle 1000+ unique IDs efficiently

## Files Modified

### Backend
- `backend/app/utils/temporal_aggregation.py` (NEW)
- `backend/app/routers/search_multistage.py`

### Frontend
- `frontend/src/components/TemporalToggle.jsx` (NEW)
- `frontend/src/components/TemporalIDResults.jsx` (NEW)
- `frontend/src/components/TemporalTupleResults.jsx` (NEW)
- `frontend/src/services/api.js`
- `frontend/src/App.jsx`
- `frontend/src/layouts/Header.jsx`
- `frontend/src/layouts/MainContent.jsx`
