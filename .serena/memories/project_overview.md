# FindingModelForge Project Overview

## Purpose

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings, using the `findingmodel` library
(0.3.1+) for core functionality.

## Key Features

- AI-powered finding model generation and similarity detection
- Step-by-step finding model creation workflow with draft saving
- **Draft management system with autosave functionality**
- GitHub OAuth authentication with JWT tokens
- MongoDB persistence with Redis caching (Redis REQUIRED)
- Modern frontend with Tailwind CSS, Alpine.js, and Vite
- **Resume workflow from drafts**
- **Submit and lock draft functionality**

## Tech Stack

### Backend

- **FastAPI** (0.115.0+) - Async web framework with automatic API documentation
- **Python 3.12+** - With extensive type hinting throughout
- **Pydantic** - Data validation for models, API contracts, and config
- **Motor** - Async MongoDB driver for data persistence
- **Redis** - **REQUIRED** for session management (not optional)
- **JWT + GitHub OAuth** - Authentication system with HTTP-only cookies
- **Loguru** - Structured logging framework

### Frontend

- **Jinja2** - Server-side templating with component macros
- **Tailwind CSS v4** - Utility-first CSS with dark mode support
- **Alpine.js** - Reactive JavaScript for interactivity
- **Flowbite** - Pre-built UI components (data-attribute driven)
- **Vite** - Modern frontend build system with hot reload
- **HTMX** - For dynamic server-driven interactions

### Core Domain Library

- **findingmodel** (0.3.1+) - Core library for finding model operations
  - Provides `FindingInfo`, `FindingModelFull`, `Index`, `Person`, `Organization` models
  - Tools for AI-powered model generation and similarity detection

## Infrastructure Requirements

### Redis (REQUIRED)
- **Purpose**: Session management for creation workflow
- **Behavior**: Server fails to start if Redis unavailable
- **Configuration**: `REDIS_HOST`, `REDIS_PORT` in `.env` (no enable/disable flag)
- **Implementation**: [`app/main.py:34-51`](app/main.py#L34-L51) checks health on startup
- **Error**: Raises `RuntimeError` with clear message if unavailable

### MongoDB (REQUIRED)
- **Purpose**: Primary data store for all application data
- **Behavior**: Server fails to start if MongoDB unavailable
- **Configuration**: `MONGODB_URI`, `MONGODB_DB` in `.env`

## Draft System Features

- **Autosave on Step 4**: Automatically saves drafts during attribute editing
- **Draft Repository**: MongoDB-backed draft storage with action logging
- **Draft States**: `draft` (editable) and `submitted` (locked)
- **Resume Workflow**: Can resume from draft at any step
- **Session Adoption**: Automatic draft state recovery on session loss
- **User-Scoped Drafts**: Each user's drafts are isolated

## Current Branch

- Working branch: `dev`
- Main branch: `main`

## Environment

- Platform: Darwin (macOS)
- Python: 3.12+
- Node.js required for frontend build tools
