import pytest
from appy import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Registro perfiles Web3' in response.data

def test_submit_missing_fields(client):
    response = client.post('/submit', data={})
    assert response.status_code == 400
    assert b'Faltan datos' in response.data

def test_admin_login_page(client):
    response = client.get('/admin/login')
    assert response.status_code == 200
    assert b'Acceso Admin' in response.data

def test_admin_dashboard_requires_login(client):
    response = client.get('/admin/dashboard')
    # Debe redirigir al login si no está autenticado
    assert response.status_code == 302
    assert '/admin/login' in response.headers['Location']
