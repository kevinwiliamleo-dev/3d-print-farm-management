#!/usr/bin/env python
import requests
import time
from pathlib import Path

time.sleep(2)

file_path = Path('data/uploads/test_model.3mf')
print(f'Testing upload with: {file_path}')
print(f'File exists: {file_path.exists()}')
print(f'Is file: {file_path.is_file()}')

if file_path.exists():
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            r = requests.post('http://localhost:8002/api/jobs/upload', files=files, timeout=10)
            print(f'Status Code: {r.status_code}')
            if r.status_code == 200:
                print('✓ SUCCESS!')
                print(f'Job: {r.json()}')
            else:
                print(f'Error: {r.text}')
    except Exception as e:
        print(f'Exception: {type(e).__name__}: {e}')
else:
    print('File not found!')
