import pytest

from app import create_app, db
from config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / 'satura-game-routes.db'

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    flask_app = create_app(LocalTestConfig)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, username='P1_Test', password='test123'):
    return client.post('/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=False)


def _create_game(client):
    _login(client)
    response = client.post('/game', json={})
    assert response.status_code == 201
    game_id = response.get_json()['game_id']
    assert game_id
    return game_id


def test_routes_require_login_for_compile_and_deploy(client):
    _login(client)
    create_response = client.post('/game', json={})
    game_id = create_response.get_json()['game_id']

    client.get('/logout')

    compile_response = client.post(f'/game/{game_id}/compile', json={
        'player': 1,
        'source': '',
    }, follow_redirects=False)
    deploy_response = client.post(f'/game/{game_id}/deploy', json={
        'player': 1,
        'source': '',
    }, follow_redirects=False)

    assert compile_response.status_code == 302
    assert '/login' in compile_response.headers['Location']
    assert deploy_response.status_code == 302
    assert '/login' in deploy_response.headers['Location']


def test_routes_enforce_player_authorization(client):
    game_id = _create_game(client)
    client.get('/logout')
    _login(client, username='P2_Test', password='test123')

    response = client.post(f'/game/{game_id}/compile', json={
        'player': 1,
        'source': '',
    })

    assert response.status_code == 403
    assert response.get_json()['error'] == 'forbidden'


def test_state_rejects_unknown_game_id(client):
    response = client.get('/game/not-a-real-id/state')
    assert response.status_code == 404


def test_page_routes(client):
    game_new_response = client.get('/game/new')
    assert game_new_response.status_code == 200

    game_id = _create_game(client)
    game_response = client.get(f'/game/{game_id}')
    assert game_response.status_code == 200

    missing_game_response = client.get('/game/not-a-real-id')
    assert missing_game_response.status_code == 404


def test_legacy_new_game_route_redirects(client):
    response = client.get('/new-game', follow_redirects=False)
    assert response.status_code == 302
    assert '/game/new' in response.headers['Location']
