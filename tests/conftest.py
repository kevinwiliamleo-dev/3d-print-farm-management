"""
Test fixtures and mock MQTT client for testing
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.main import app
from src.database.db import Base, get_db
from src.services.bambu_service import BambuLabMQTTClient


# ==================== Database Setup ====================

@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Create test SQLite database for testing"""
    # Use file-based database to avoid threading issues
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Store for later use in override_get_db
    yield SessionLocal, engine


# ==================== API Client ====================

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client for FastAPI with test database"""
    SessionLocal, engine = test_db
    
    # Create override function
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # Override the get_db dependency with our test database
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    yield client
    
    # Clean up
    app.dependency_overrides.clear()


# ==================== Mock MQTT Client ====================

class MockMQTTClient:
    """Mock MQTT client that simulates Bambu Lab responses"""
    
    def __init__(self):
        self.mqtt_connected = False
        self.printer_status = "idle"
        self.current_print_progress = 0
        self.published_messages = []
        self.callbacks = {}
        
    def connect(self):
        """Simulate successful connection"""
        self.mqtt_connected = True
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        self.mqtt_connected = False
        return True
    
    def send_gcode_to_printer(self, gcode_path):
        """Mock G-code send"""
        self.published_messages.append({
            "type": "gcode",
            "path": gcode_path
        })
        return True
    
    def start_print(self):
        """Mock print start"""
        self.printer_status = "printing"
        self.current_print_progress = 0
        self.published_messages.append({"type": "start_print"})
        return True
    
    def pause_print(self):
        """Mock print pause"""
        self.published_messages.append({"type": "pause_print"})
        return True
    
    def resume_print(self):
        """Mock print resume"""
        self.published_messages.append({"type": "resume_print"})
        return True
    
    def stop_print(self):
        """Mock print stop"""
        self.printer_status = "idle"
        self.published_messages.append({"type": "stop_print"})
        return True
    
    def trigger_auto_eject(self):
        """Mock auto-eject"""
        self.published_messages.append({"type": "auto_eject"})
        return True
    
    def get_printer_status(self):
        """Mock get printer status"""
        return {
            "printer_id": "03900D5A2402051",
            "printer_status": self.printer_status,
            "mqtt_connected": self.mqtt_connected,
            "current_print_progress": self.current_print_progress,
        }
    
    def is_printer_online(self):
        """Check if printer online"""
        return self.mqtt_connected
    
    def is_printer_idle(self):
        """Check if printer idle"""
        return self.mqtt_connected and self.printer_status == "idle"
    
    def get_print_progress(self):
        """Get print progress"""
        return self.current_print_progress
    
    def simulate_print_progress(self, progress):
        """Simulate print progress update"""
        self.current_print_progress = progress
    
    def simulate_print_complete(self):
        """Simulate print completion"""
        self.printer_status = "idle"
        self.current_print_progress = 100
        if self.callbacks.get("on_print_complete"):
            self.callbacks["on_print_complete"]()


@pytest.fixture
def mock_bambu_client():
    """Provide mock MQTT client"""
    return MockMQTTClient()


# ==================== Test Data ====================

@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "loop_count": 3,
        "layer_height": 0.2,
        "infill_density": 15,
    }


@pytest.fixture
def sample_printer_data():
    """Sample printer data for testing"""
    return {
        "printer_id": "03900D5A2402051",
        "printer_name": "Bambu Lab A1 #1",
    }


@pytest.fixture
def sample_gcode_file(tmp_path):
    """Create sample G-code file for testing"""
    gcode_file = tmp_path / "test_model.gcode"
    gcode_content = """G28
G29
M104 S220
M109 S220
G0 X0 Y0 Z0.2
G1 X100 Y100 F3000
G1 X0 Y100 F3000
M104 S0
M109 S0
"""
    gcode_file.write_text(gcode_content)
    return str(gcode_file)


@pytest.fixture
def sample_3mf_file(tmp_path):
    """Create sample 3MF file for testing"""
    model_file = tmp_path / "test_model.3mf"
    # Write minimal 3MF content (it's a ZIP file)
    import zipfile
    with zipfile.ZipFile(model_file, 'w') as zf:
        zf.writestr("_rels/.rels", '<Relationships></Relationships>')
        zf.writestr("[Content_Types].xml", '<Types></Types>')
    return model_file


@pytest.fixture
def sample_stl_file(tmp_path):
    """Create sample STL file for testing"""
    model_file = tmp_path / "test_model.stl"
    # Write minimal STL content (ASCII STL)
    with open(model_file, 'w') as f:
        f.write("solid test_model\n")
        f.write("  facet normal 0 0 1\n")
        f.write("    outer loop\n")
        f.write("      vertex 0 0 0\n")
        f.write("      vertex 1 0 0\n")
        f.write("      vertex 0 1 0\n")
        f.write("    endloop\n")
        f.write("  endfacet\n")
        f.write("endsolid test_model\n")
    return model_file


# ==================== Utility Functions ====================

def create_test_job(client, loop_count=2):
    """Helper to create a test job"""
    # Create temporary 3mf file
    import tempfile
    import zipfile
    
    with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
        with zipfile.ZipFile(tmp, 'w') as zf:
            zf.writestr("_rels/.rels", '<Relationships></Relationships>')
        tmp_path = tmp.name
    
    # Upload file
    with open(tmp_path, 'rb') as f:
        response = client.post(
            "/api/jobs/upload",
            files={"file": f},
            data={"loop_count": loop_count}
        )
    
    import os
    os.unlink(tmp_path)
    
    assert response.status_code == 200
    return response.json()


def create_test_printer(client, printer_id="03900D5A2402051"):
    """Helper to register a test printer"""
    response = client.post(
        "/api/printers",
        json={
            "printer_id": printer_id,
            "printer_name": "Bambu Lab A1 Test"
        }
    )
    assert response.status_code == 201
    return response.json()


def add_job_to_queue(client, job_id, printer_id):
    """Helper to add job to queue"""
    response = client.post(
        "/api/queue/add",
        json={
            "job_id": job_id,
            "printer_id": printer_id,
        }
    )
    assert response.status_code == 200
    return response.json()
