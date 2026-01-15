```
cooking-ai-agent/
│
├── README.md                          # Project documentation & naming conventions
├── requirements.txt                   # Python dependencies
├── .env                               # Environment configuration (COPY from .env.example)
├── .env.example                       # Environment template
│
├── src/                              # Main application source code
│   ├── __init__.py                   # Package initialization
│   ├── main.py                       # FastAPI application entry point
│   ├── config.py                     # Configuration management
│   │
│   ├── api/                          # API endpoints (routers)
│   │   ├── __init__.py
│   │   ├── jobs.py                   # Job upload & management endpoints
│   │   ├── queue.py                  # Queue management endpoints
│   │   ├── printers.py               # Printer control endpoints
│   │   └── history.py                # Print history endpoints
│   │
│   ├── services/                     # Business logic & services
│   │   ├── __init__.py
│   │   ├── job_service.py            # Job processing service
│   │   ├── queue_service.py          # Queue management service
│   │   ├── printer_service.py        # Printer control service
│   │   ├── slicer_service.py         # OrcaSlicer integration
│   │   └── mqtt_service.py           # MQTT communication
│   │
│   ├── database/                     # Database & ORM
│   │   ├── __init__.py
│   │   └── db.py                     # SQLAlchemy models & session
│   │
│   ├── models/                       # Pydantic schemas for API
│   │   ├── __init__.py
│   │   └── schemas.py                # Request/response models
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── slicer.py                 # OrcaSlicer wrapper & helpers
│       ├── file_handler.py           # File upload/handling utilities
│       └── mqtt_client.py            # MQTT client wrapper
│
├── data/                             # Data storage
│   ├── farm.db                       # SQLite database (auto-created)
│   ├── uploads/                      # Uploaded model files (.3mf, .stl)
│   └── gcode/                        # Generated G-code files
│
├── logs/                             # Application logs
│   └── app.log                       # Debug and error logs
│
├── frontend/                         # React web interface (Phase 3)
│   ├── package.json
│   ├── src/
│   ├── public/
│   └── README.md
│
├── tests/                            # Unit & integration tests (Phase 4)
│   ├── test_jobs.py
│   ├── test_queue.py
│   ├── test_slicer.py
│   └── test_mqtt.py
│
├── scripts/                          # Utility scripts
│   ├── init_db.py                    # Initialize database
│   ├── reset_db.py                   # Reset database
│   └── test_orca.py                  # Test OrcaSlicer installation
│
└── .github/                          # GitHub related files
    └── copilot-instructions.md       # Development guidelines
```

## 📁 Directory Purposes

### `src/main.py`
- FastAPI application entry point
- Request routing
- Middleware configuration
- Startup/shutdown hooks

### `src/config.py`
- Environment variables loading
- Configuration constants
- Path management
- Feature flags

### `src/database/db.py`
- SQLAlchemy database setup
- ORM model definitions (Job, Queue, PrintHistory, etc)
- Database session management
- Table schemas with proper field naming

### `src/models/schemas.py`
- Pydantic models for API validation
- Request/response schemas
- Enums for status values
- Type safety for API endpoints

### `src/api/` routers
- FastAPI route handlers
- HTTP methods (GET, POST, PUT, DELETE)
- Parameter validation
- Response formatting

### `src/services/` business logic
- Core application logic
- Database operations
- OrcaSlicer integration
- MQTT communication
- Queue management

### `src/utils/` helper functions
- File handling utilities
- OrcaSlicer CLI wrapper
- MQTT client wrapper
- Validation functions

### `data/` directories
- **farm.db**: SQLite database (do not commit)
- **uploads/**: Temporary uploaded files (do not commit)
- **gcode/**: Generated G-code files (do not commit)

### `logs/` directory
- Application logs (do not commit)
- Debugging information

## 🔧 Variable Naming Convention Location
See [README.md - Naming Conventions & Code Standards](../README.md#-naming-conventions--code-standards)

All variable names follow this structure:
- **Database fields**: job_id, printer_id, queue_position, etc
- **Python functions**: slice_model(), send_gcode_to_printer(), etc
- **Frontend JS**: jobId, printerId, queuePosition, etc

## 📝 Development Workflow

1. **Create API endpoint** in `src/api/`
2. **Create request/response schema** in `src/models/schemas.py`
3. **Implement service logic** in `src/services/`
4. **Add database operations** in `src/database/db.py` (models) and service
5. **Test endpoint** with pytest
6. **Update documentation** in README.md

## ⚠️ Files NOT to Commit
- `.env` (has credentials)
- `data/farm.db`
- `data/uploads/*`
- `data/gcode/*`
- `logs/*`
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc`
