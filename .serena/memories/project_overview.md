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
- MongoDB persistence with Redis caching
- Modern frontend with Tailwind CSS, Alpine.js, and Vite
- **Resume workflow from drafts**
- **Submit and lock draft functionality**

## Tech Stack

### Backend

- **FastAPI** (0.115.0+) - Async web framework with automatic API documentation
- **Python 3.12+** - With extensive type hinting throughout
- **Pydantic** - Data validation for models, API contracts, and config
- **Motor** - Async MongoDB driver for data persistence
- **Redis** - Optional caching layer (configurable via env)
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

## Draft System Features

- **Autosave on Step 4**: Automatically saves drafts during attribute editing
- **Draft Repository**: MongoDB-backed draft storage with action logging
- **Draft States**: `draft` (editable) and `submitted` (locked)
- **Resume Workflow**: Can resume from draft at any step
- **Session Adoption**: Automatic draft state recovery on session loss
- **User-Scoped Drafts**: Each user's drafts are isolated

## Current Branch

- Working branch: `feature/finding-model-draft-saving`
- Main branch: `main`

## Environment

- Platform: Darwin (macOS)
- Python: 3.12+
- Node.js required for frontend build tools
