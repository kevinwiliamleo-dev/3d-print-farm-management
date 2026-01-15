"""
Integration tests for Job API endpoints
Tests job upload, listing, and management
"""
import pytest
import tempfile
import zipfile
import os


class TestJobUpload:
    """Test job upload functionality"""
    
    def test_upload_3mf_file(self, client, sample_3mf_file):
        """Test uploading a 3MF file"""
        # Use the sample file from fixture
        with open(sample_3mf_file, 'rb') as f:
            response = client.post(
                "/api/jobs/upload",
                files={"file": f},
                data={"loop_count": 5}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["job_name"] == "test_model"
        assert data["loop_count"] == 5
        assert data["status"] == "pending"
        
        print(f"✅ Job uploaded successfully: job_id={data['job_id']}")
    
    def test_upload_stl_file(self, client, sample_stl_file):
        """Test uploading a STL file"""
        # Use the sample file from fixture
        with open(sample_stl_file, 'rb') as f:
            response = client.post(
                "/api/jobs/upload",
                files={"file": f},
                data={"loop_count": 2}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_name"] == "test_model"
        assert data["loop_count"] == 2
        
        print(f"✅ STL file uploaded: job_id={data['job_id']}")
    
    def test_upload_invalid_file_type(self, client):
        """Test uploading invalid file type"""
        # Create temporary TXT file (invalid)
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"This is not a model file")
            tmp_path = tmp.name
        
        try:
            # Upload file
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/jobs/upload",
                    files={"file": f},
                    data={"loop_count": 1}
                )
            
            # Should fail
            assert response.status_code == 400
            
            print(f"✅ Invalid file type rejected correctly")
            
        finally:
            os.unlink(tmp_path)
    
    def test_upload_with_invalid_loop_count(self, client):
        """Test uploading with invalid loop count"""
        with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
            with zipfile.ZipFile(tmp, 'w') as zf:
                zf.writestr("_rels/.rels", '<Relationships></Relationships>')
            tmp_path = tmp.name
        
        try:
            # Upload with invalid loop count
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/jobs/upload",
                    files={"file": f},
                    data={"loop_count": 0}  # Invalid
                )
            
            # Should fail
            assert response.status_code == 400
            
            print(f"✅ Invalid loop count rejected")
            
        finally:
            os.unlink(tmp_path)


class TestJobListing:
    """Test job listing and retrieval"""
    
    def test_list_jobs_empty(self, client):
        """Test listing jobs when no jobs exist"""
        response = client.get("/api/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 0
        assert data["jobs"] == []
        
        print(f"✅ Empty job list returned correctly")
    
    def test_list_jobs_with_data(self, client):
        """Test listing jobs after creating some"""
        # Create 3 jobs
        job_ids = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
                with zipfile.ZipFile(tmp, 'w') as zf:
                    zf.writestr("_rels/.rels", '<Relationships></Relationships>')
                tmp_path = tmp.name
            
            try:
                with open(tmp_path, 'rb') as f:
                    response = client.post(
                        "/api/jobs/upload",
                        files={"file": f},
                        data={"loop_count": i + 1}
                    )
                job_ids.append(response.json()["job_id"])
            finally:
                os.unlink(tmp_path)
        
        # List all jobs
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 3
        assert len(data["jobs"]) == 3
        
        # Verify job data
        for i, job in enumerate(data["jobs"]):
            assert job["job_id"] in job_ids
            assert job["loop_count"] == i + 1
            assert job["status"] == "pending"
        
        print(f"✅ Listed {len(data['jobs'])} jobs correctly")
    
    def test_get_specific_job(self, client):
        """Test getting a specific job by ID"""
        # Create a job
        with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
            with zipfile.ZipFile(tmp, 'w') as zf:
                zf.writestr("_rels/.rels", '<Relationships></Relationships>')
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/jobs/upload",
                    files={"file": f},
                    data={"loop_count": 7}
                )
            
            job_id = response.json()["job_id"]
            
            # Get specific job
            response = client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["loop_count"] == 7
            
            print(f"✅ Retrieved specific job: job_id={job_id}")
            
        finally:
            os.unlink(tmp_path)
    
    def test_get_nonexistent_job(self, client):
        """Test getting a job that doesn't exist"""
        response = client.get("/api/jobs/99999")
        
        assert response.status_code == 404
        
        print(f"✅ Nonexistent job returns 404")


class TestJobDeletion:
    """Test job deletion"""
    
    def test_delete_job(self, client):
        """Test deleting a job"""
        # Create a job
        with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
            with zipfile.ZipFile(tmp, 'w') as zf:
                zf.writestr("_rels/.rels", '<Relationships></Relationships>')
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as f:
                response = client.post(
                    "/api/jobs/upload",
                    files={"file": f},
                    data={"loop_count": 1}
                )
            
            job_id = response.json()["job_id"]
            
            # Delete job
            response = client.delete(f"/api/jobs/{job_id}")
            assert response.status_code == 200
            
            # Verify job is deleted
            response = client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 404
            
            print(f"✅ Job deleted successfully: job_id={job_id}")
            
        finally:
            os.unlink(tmp_path)
