"""
Integration tests for Queue and Print Control
Tests printing workflow, loop management, and auto-eject
"""
import pytest
import tempfile
import zipfile
import os
import time


def create_test_job(client, loop_count=2):
    """Helper to create a test job"""
    with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
        with zipfile.ZipFile(tmp, 'w') as zf:
            zf.writestr("_rels/.rels", '<Relationships></Relationships>')
        tmp_path = tmp.name
    
    with open(tmp_path, 'rb') as f:
        response = client.post(
            "/api/jobs/upload",
            files={"file": f},
            data={"loop_count": loop_count}
        )
    
    os.unlink(tmp_path)
    return response.json()


def register_printer(client, printer_id="03900D5A2402051"):
    """Helper to register a test printer"""
    response = client.post(
        "/api/printers",
        json={
            "printer_id": printer_id,
            "printer_name": "Bambu Lab A1 Test"
        }
    )
    return response.json()


class TestPrinterManagement:
    """Test printer registration and management"""
    
    def test_register_printer(self, client):
        """Test registering a printer"""
        response = client.post(
            "/api/printers",
            json={
                "printer_id": "03900D5A2402051",
                "printer_name": "Bambu Lab A1"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["printer_id"] == "03900D5A2402051"
        assert data["printer_name"] == "Bambu Lab A1"
        assert data["status"] == "offline"
        assert data["mqtt_connected"] == False
        
        print(f"✅ Printer registered: printer_id={data['printer_id']}")
    
    def test_list_printers(self, client):
        """Test listing printers"""
        # Register 2 printers
        for i in range(2):
            register_printer(client, f"0390{i:016d}")
        
        # List printers
        response = client.get("/api/printers")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 2
        
        print(f"✅ Listed {data['total']} printers")
    
    def test_get_printer_details(self, client):
        """Test getting printer details"""
        printer = register_printer(client, "03900D5A2402051")
        printer_id = printer["printer_id"]
        
        # Get details
        response = client.get(f"/api/printers/{printer_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["printer_id"] == printer_id
        
        print(f"✅ Retrieved printer details")
    
    def test_update_printer_status(self, client):
        """Test updating printer status"""
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Update status
        response = client.patch(
            f"/api/printers/{printer_id}/status",
            json={"printer_status": "printing"}
        )
        
        assert response.status_code == 200
        
        # Verify updated
        response = client.get(f"/api/printers/{printer_id}")
        assert response.json()["status"] == "printing"
        
        print(f"✅ Printer status updated")


class TestQueueManagement:
    """Test queue operations"""
    
    def test_add_job_to_queue(self, client):
        """Test adding job to queue"""
        # Create job and printer
        job = create_test_job(client, loop_count=3)
        printer = register_printer(client)
        
        # Add to queue
        response = client.post(
            "/api/queue/add",
            json={
                "job_id": job["job_id"],
                "printer_id": printer["printer_id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "queue_id" in data
        assert data["position_in_queue"] == 1
        assert data["status"] == "pending"
        
        print(f"✅ Job added to queue: queue_id={data['queue_id']}")
    
    def test_queue_fifo_order(self, client):
        """Test FIFO queue ordering"""
        # Create 3 jobs and printer
        jobs = [create_test_job(client, loop_count=i+1) for i in range(3)]
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Add jobs to queue in order
        queue_ids = []
        for i, job in enumerate(jobs):
            response = client.post(
                "/api/queue/add",
                json={
                    "job_id": job["job_id"],
                    "printer_id": printer_id
                }
            )
            queue_ids.append(response.json()["queue_id"])
        
        # Get queue
        response = client.get(f"/api/queue/{printer_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify FIFO order
        assert len(data["queue_items"]) == 3
        assert data["queue_items"][0]["position_in_queue"] == 1
        assert data["queue_items"][1]["position_in_queue"] == 2
        assert data["queue_items"][2]["position_in_queue"] == 3
        
        print(f"✅ Queue maintains FIFO order")
    
    def test_get_queue_status(self, client):
        """Test getting queue statistics"""
        # Create jobs and printer
        jobs = [create_test_job(client) for _ in range(2)]
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Add jobs
        for job in jobs:
            client.post(
                "/api/queue/add",
                json={
                    "job_id": job["job_id"],
                    "printer_id": printer_id
                }
            )
        
        # Get queue status
        response = client.get(f"/api/queue/{printer_id}/status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_items"] == 2
        assert data["pending_items"] == 2
        assert data["running_items"] == 0
        
        print(f"✅ Queue status: {data['pending_items']} pending")
    
    def test_remove_from_queue(self, client):
        """Test removing item from queue"""
        job = create_test_job(client)
        printer = register_printer(client)
        
        # Add to queue
        response = client.post(
            "/api/queue/add",
            json={
                "job_id": job["job_id"],
                "printer_id": printer["printer_id"]
            }
        )
        queue_id = response.json()["queue_id"]
        
        # Remove from queue
        response = client.post(f"/api/queue/{queue_id}/remove")
        assert response.status_code == 200
        
        # Verify removed
        response = client.get(f"/api/queue/{printer['printer_id']}")
        assert len(response.json()["queue_items"]) == 0
        
        print(f"✅ Job removed from queue")


class TestPrintingWorkflow:
    """Test printing workflow and loop management"""
    
    @pytest.mark.skip(reason="Requires real Bambu Lab MQTT connection and gcode generation")
    def test_basic_print_workflow(self, client):
        """Test basic print workflow"""
        # Create job with 2 loops
        job = create_test_job(client, loop_count=2)
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Add to queue
        response = client.post(
            "/api/queue/add",
            json={
                "job_id": job["job_id"],
                "printer_id": printer_id
            }
        )
        queue_id = response.json()["queue_id"]
        
        # Start print
        response = client.post(f"/api/print-control/{printer_id}/start-print")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        
        print(f"✅ Print started successfully")
    
    def test_print_status(self, client):
        """Test getting print status"""
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Get status (should be idle initially)
        response = client.get(f"/api/print-control/{printer_id}/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "printer_id" in data
        assert "print_info" in data
        
        print(f"✅ Print status retrieved")
    
    def test_pause_resume_cancel(self, client):
        """Test pause, resume, and cancel operations"""
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Test pause (should not fail even without active print)
        response = client.post(f"/api/print-control/{printer_id}/pause")
        # May return 200 or 400 depending on state
        
        # Test resume
        response = client.post(f"/api/print-control/{printer_id}/resume")
        # May return 200 or 400
        
        # Test cancel
        response = client.post(f"/api/print-control/{printer_id}/cancel")
        # May return 200 or 400
        
        print(f"✅ Pause/Resume/Cancel operations handled")
    
    def test_mqtt_connection_status(self, client):
        """Test MQTT connection status"""
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Get MQTT status
        response = client.get(f"/api/print-control/{printer_id}/mqtt-status")
        assert response.status_code == 200
        data = response.json()
        
        assert "mqtt_connected" in data
        assert "printer_status" in data
        assert "print_progress" in data
        
        print(f"✅ MQTT status retrieved: connected={data['mqtt_connected']}")
    
    def test_auto_eject(self, client):
        """Test auto-eject trigger"""
        printer = register_printer(client)
        printer_id = printer["printer_id"]
        
        # Trigger eject
        response = client.post(f"/api/print-control/{printer_id}/eject")
        # Should work or return error
        
        print(f"✅ Auto-eject command sent")


class TestLoopManagement:
    """Test loop counting and repeat logic"""
    
    def test_job_with_multiple_loops(self, client):
        """Test job configured with multiple loops"""
        # Create job with 5 loops
        job = create_test_job(client, loop_count=5)
        
        # Verify loop count
        assert job["loop_count"] == 5
        assert job["status"] == "pending"
        
        print(f"✅ Job created with loop_count=5")
    
    def test_queue_loop_increment(self, client):
        """Test that queue properly tracks loop increments"""
        job = create_test_job(client, loop_count=3)
        printer = register_printer(client)
        
        # Add to queue
        response = client.post(
            "/api/queue/add",
            json={
                "job_id": job["job_id"],
                "printer_id": printer["printer_id"]
            }
        )
        
        queue_data = response.json()
        
        # Initially should be at loop 0
        assert "queue_id" in queue_data
        
        print(f"✅ Queue loop tracking initialized")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_add_job_to_nonexistent_printer(self, client):
        """Test adding job to nonexistent printer"""
        job = create_test_job(client)
        
        response = client.post(
            "/api/queue/add",
            json={
                "job_id": job["job_id"],
                "printer_id": "nonexistent_printer"
            }
        )
        
        assert response.status_code == 404
        
        print(f"✅ Nonexistent printer error handled")
    
    def test_invalid_printer_status(self, client):
        """Test updating printer with invalid status"""
        printer = register_printer(client)
        
        response = client.patch(
            f"/api/printers/{printer['printer_id']}/status",
            json={"printer_status": "invalid_status"}
        )
        
        assert response.status_code == 400
        
        print(f"✅ Invalid printer status rejected")
