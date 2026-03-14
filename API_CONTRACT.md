# API Contract Documentation

## Overview
This document outlines the API contract between the frontend (React/Vite) and backend (Flask) components of the Mathematical Solver Platform.

## Base Configuration
- **Backend URL**: `http://127.0.0.1:5000`
- **Frontend URL**: `http://localhost:5173` (Vite dev server)
- **API Prefix**: `/api`

## Endpoints

### 1. Solve Differential Equation
**Endpoint**: `POST /api/math/solve`

**Request Body**:
```json
{
  "formula": "y'' + y = 0",
  "conditions": [
    {"t": 0, "val": 1}
  ],
  "tMax": 10
}
```

**Response**:
```json
{
  "success": true,
  "meta": {
    "latex": "y'' + y = 0",
    "order": 2,
    "linearity": "linear"
  },
  "symbolic": {
    "success": true,
    "solution": "...",
    "data": {...}
  },
  "numerical": {
    "success": true,
    "data": {...}
  },
  "pinn": {
    "success": true,
    "data": {...}
  }
}
```

### 2. Stream PINN Training
**Endpoint**: `POST /api/math/solve/stream`

**Request Body**:
```json
{
  "formula": "y'' + y = 0",
  "conditions": [
    {"t": 0, "val": 1}
  ],
  "tMax": 10
}
```

**Response**: Server-Sent Events (SSE) Stream

**Event Types**:
- `epoch_update`: Training progress update
- `training_complete`: Training finished
- `training_error`: Training failed

**Epoch Update Event**:
```json
{
  "type": "epoch_update",
  "epoch": 100,
  "loss": {
    "total": 0.001,
    "physics": 0.0009,
    "boundary": 0.0001
  },
  "function_data": {
    "function_data": {
      "x": [0, 0.1, 0.2, ...],
      "y": [1.0, 0.995, 0.980, ...]
    },
    "metadata": {
      "domain": [0, 10],
      "points": 100,
      "snapshot_timestamp": 1640995200.0
    }
  },
  "timestamp": 1640995200.0
}
```

**Training Complete Event**:
```json
{
  "type": "training_complete",
  "success": true,
  "final_data": {
    "function_data": {...},
    "metadata": {...}
  },
  "timestamp": 1640995200.0
}
```

**Training Error Event**:
```json
{
  "type": "training_error",
  "error": "Error message description",
  "timestamp": 1640995200.0
}
```

### 3. Export Data
**Endpoint**: `POST /api/math/export/{format_type}`

**Parameters**:
- `format_type`: `csv` or `json`

**Request Body**:
```json
{
  "x": [0, 0.1, 0.2, ...],
  "y": [1.0, 0.995, 0.980, ...],
  "meta": {
    "source": "MathPlatform License Project"
  }
}
```

**Response**: File download with appropriate headers

## CORS Configuration
The backend is configured to accept requests from:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:3000`

Allowed methods: `GET`, `POST`, `OPTIONS`
Allowed headers: `Content-Type`, `Cache-Control`

## Error Handling
All endpoints return consistent error responses:
```json
{
  "success": false,
  "error": "Error description"
}
```

For SSE streams, errors are sent as SSE events with type `training_error`.

## Data Format Standards
- All numeric values are sent as numbers (not strings)
- Arrays are used for x,y coordinate data
- Timestamps use Unix epoch format (seconds)
- Boolean values use `true`/`false`

## Frontend Configuration
The frontend uses Vite proxy to forward `/api/*` requests to the backend:
```javascript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:5000',
    changeOrigin: true,
    secure: false,
    ws: true
  }
}
```
