"""Reset queue and job status to pending for testing"""
from src.database.db import SessionLocal, Queue, Job

db = SessionLocal()

# Reset queue to pending
q = db.query(Queue).filter(Queue.queue_id == 1).first()
if q:
    q.status = 'pending'
    q.started_at = None
    print(f"Reset queue_id=1 to pending")

# Reset job to pending
job = db.query(Job).filter(Job.job_id == 26).first()
if job:
    job.status = 'pending'
    print(f"Reset job_id=26 to pending")

db.commit()
print("Changes committed!")

# Verify
q = db.query(Queue).filter(Queue.queue_id == 1).first()
job = db.query(Job).filter(Job.job_id == 26).first()
print(f"Queue status: {q.status if q else 'Not found'}")
print(f"Job status: {job.status if job else 'Not found'}")

db.close()
