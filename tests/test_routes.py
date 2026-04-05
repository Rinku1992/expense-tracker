import io
import pytest


class TestIndex:
    def test_index_page(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Upload' in response.data


class TestDashboard:
    def test_dashboard_page(self, client):
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data


class TestMonthlySummaryAPI:
    def test_empty_summary(self, client):
        response = client.get('/api/monthly-summary')
        assert response.status_code == 200
        assert response.get_json() == []


class TestUpload:
    def test_upload_no_file(self, client):
        response = client.post('/upload', follow_redirects=True)
        assert response.status_code == 200
        assert b'No file selected' in response.data

    def test_upload_invalid_extension(self, client):
        data = {'file': (io.BytesIO(b'test'), 'test.txt')}
        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
        assert b'Invalid file type' in response.data


class TestTransactionsAPI:
    def test_invalid_type(self, client):
        response = client.get('/api/transactions/2025/1/invalid')
        assert response.status_code == 400


class TestExport:
    def test_export_empty(self, client):
        response = client.get('/export', follow_redirects=True)
        assert response.status_code == 200
