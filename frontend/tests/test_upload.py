import io
import os
import sys
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import app

def test_upload_backend_unavailable(monkeypatch):
    def mock_post(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Backend unavailable")
    monkeypatch.setattr(requests, "post", mock_post)

    client = app.test_client()
    data = {
        'file': (io.BytesIO(b'dummy'), 'test.pdf')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 500
    payload = response.get_json()
    assert 'error' in payload
    assert 'Backend unavailable' in payload['error']
