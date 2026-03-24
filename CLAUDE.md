# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZenClean (禅清) is a Windows C-drive cleaning utility built with Python and Flet (Flutter for Python). It combines AI-powered analysis with low-level system operations for deep cleaning capabilities.

## Commands

### Development
```bash
# Run the application (requires admin privileges for full functionality)
python src/main.py

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For building/packaging
```

### Building
```bash
# Build portable release (outputs to dist/ZenClean/)
python scripts/build_release.py

# Build installer (requires Inno Setup)
python scripts/build_installer.py

# Manual PyInstaller build
pyinstaller zenclean.spec --clean
```

### Testing
```bash
# Run specific test file
python -m pytest tests/test_engine.py -v

# Run all tests
python -m pytest tests/ -v
```

## Architecture

### Source Structure
```
src/
├── main.py              # Entry point, UAC elevation, IPC listener, tray setup
├── config/
│   ├── settings.py      # Global configuration, scan targets (150+ paths)
│   └── file_kb.json     # File knowledge base for AI classification
├── core/                # Business logic layer
│   ├── scanner.py       # Async file scanner with message queue
│   ├── cleaner.py       # File deletion with quarantine support
│   ├── app_migrator.py  # NTFS Junction-based app migration
│   ├── migration.py     # Windows Shell API + Junction migration engine
│   ├── patch_analyzer.py # Windows Update patch cleanup
│   ├── quarantine.py    # 72-hour isolation with auto-expiry
│   ├── auth.py          # License validation (HMAC-SHA256)
│   └── safety_manager.py # Risk classification (SAFE/WARNING/CRISIS)
├── ai/
│   ├── cloud_engine.py  # Remote AI classification API
│   └── local_engine.py  # Local fallback classifier
└── ui/
    ├── app.py           # Root view manager, navigation, theming
    ├── tray_manager.py  # System tray integration
    ├── views/           # Page-level components
    └── components/      # Reusable UI widgets
```

### Key Architectural Patterns

1. **Async Scanner 2.0**: UI thread isolation via background Worker + message queue (`src/core/scanner.py`). The scanner runs in a separate process and communicates results via a queue that the UI polls.

2. **Time Machine Quarantine**: Files are moved to `%APPDATA%\ZenClean\Quarantine\` with metadata tracking. Auto-cleanup daemon removes items after 72 hours.

3. **Dual Migration Engine**: `migration.py` uses Windows Shell API (preferred) with NTFS Junction fallback for app directory relocation. Handles "ghost write-back" issues where apps continue writing to original paths.

4. **Single Instance IPC**: TCP listener on port 19528. Secondary instances connect and pass commands (e.g., right-click context menu "Analyze with ZenClean").

5. **License System**: Uses `auth.py` with HMAC-SHA256 signatures, NTP time validation, and device fingerprinting via `py-machineid`.

### Configuration Management

- `.env` file contains sensitive API keys (see `.env.example`)
- `src/config/settings.py` defines all constants including 150+ scan target paths
- User data stored in `%APPDATA%\ZenClean\`

### Flet UI Architecture

The app uses Flet's NavigationRail for sidebar navigation. Each view is a class inheriting from `ft.Column` or `ft.View`. Theme switching between dark (cyberpunk) and light (medical lab) modes is handled via `page.theme_mode` and `client_storage` for persistence.

## Web Landing Page

The `web/` directory contains a static landing page deployed at `zenclean.hwdemtv.com`:
- `index.html` - SEO-optimized with JSON-LD structured data
- `styles.css` - Local fonts (Outfit), CSS animations for scroll reveals
- `script.js` - Native Intersection Observer (no external dependencies)
- `assets/` - WebP images with PNG fallbacks

## Windows-Specific Notes

- **Admin Privileges Required**: Deep cleaning operations (Windows Update cleanup, system temp) require UAC elevation. The app auto-restarts with `runas` if not elevated.
- **VC++ Runtime Check**: App validates `vcruntime140.dll` and `msvcp140.dll` on startup, prompts user to install if missing.
- **Named Mutex**: Single instance enforced via `Global\ZenClean_SingleInstance_Mutex`.
