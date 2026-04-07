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


def _create_test_game(client, payload):
    response = client.post('/test/session', json=payload)
    assert response.status_code == 201
    game_id = response.get_json()['game_id']
    assert game_id
    return game_id


def _create_real_game(client):
    _login(client)
    response = client.post('/game', json={})
    assert response.status_code == 201
    game_id = response.get_json()['game_id']
    assert game_id
    return game_id


def test_test_session_creation_with_preset_payload(client):
    game_id = _create_test_game(client, {'preset': '15'})

    state_response = client.get(f'/test/{game_id}/state')
    assert state_response.status_code == 200
    state = state_response.get_json()

    assert state['op_limit'] == Config.TIME_CONTROL_PRESETS['15']['op_limit']
    assert state['word_rate'] == Config.TIME_CONTROL_PRESETS['15']['word_rate']
    assert len(state['board']) == Config.TIME_CONTROL_PRESETS['15']['board_size']


def test_test_session_creation_with_custom_accommodations(client):
    game_id = _create_test_game(client, {
        'preset': 'custom',
        'clock_seconds': 300,
        'board_size': 12,
        'op_limit': 33,
        'word_rate': 1.5,
        'starting_words': 17,
        'accommodations_enabled': True,
        'p1_clock_seconds': 111,
        'p2_clock_seconds': 222,
        'p1_starting_words': 11,
        'p2_starting_words': 22,
        'starting_player': 2,
    })

    state_response = client.get(f'/test/{game_id}/state')
    assert state_response.status_code == 200
    state = state_response.get_json()

    assert state['current_player'] == 2
    assert state['op_limit'] == 33
    assert state['word_rate'] == 1.5
    assert state['clock']['1'] == pytest.approx(111, abs=1e-4)
    assert state['clock']['2'] == pytest.approx(222, abs=1e-4)
    assert state['word_bank']['1'] == pytest.approx(11, abs=1e-4)
    assert state['word_bank']['2'] == pytest.approx(22, abs=1e-4)


def test_test_session_creation_with_random_starting_player(client):
    game_id = _create_test_game(client, {
        'preset': 'custom',
        'clock_seconds': 300,
        'board_size': 12,
        'op_limit': 33,
        'word_rate': 1.5,
        'starting_words': 17,
        'accommodations_enabled': True,
        'p1_clock_seconds': 111,
        'p2_clock_seconds': 222,
        'p1_starting_words': 11,
        'p2_starting_words': 22,
        'starting_player': 'random',
    })

    state_response = client.get(f'/test/{game_id}/state')
    assert state_response.status_code == 200
    state = state_response.get_json()
    assert state['current_player'] in (1, 2)


def test_test_session_creation_rejects_invalid_payload(client):
    response = client.post('/test/session', json={
        'preset': 'custom',
        'clock_seconds': 300,
        'board_size': 11,
        'op_limit': 33,
        'word_rate': 1.5,
        'starting_words': 17,
    })
    assert response.status_code == 400
    assert 'board_size' in response.get_json()['error']


def test_test_routes_do_not_require_login(client):
    game_id = _create_test_game(client, {'preset': '5'})

    state_response = client.get(f'/test/{game_id}/state')
    assert state_response.status_code == 200

    compile_response = client.post(f'/test/{game_id}/compile', json={
        'player': 1,
        'source': '',
    })
    assert compile_response.status_code == 200

    deploy_response = client.post(f'/test/{game_id}/deploy', json={
        'player': 1,
        'source': '',
    })
    assert deploy_response.status_code in (200, 422)


def test_real_routes_require_login_for_compile_and_deploy(client):
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


def test_real_routes_enforce_player_authorization(client):
    game_id = _create_real_game(client)
    client.get('/logout')
    _login(client, username='P2_Test', password='test123')

    response = client.post(f'/game/{game_id}/compile', json={
        'player': 1,
        'source': '',
    })

    assert response.status_code == 403
    assert response.get_json()['error'] == 'forbidden'


def test_test_game_ids_do_not_resolve_on_real_state_route(client):
    game_id = _create_test_game(client, {'preset': '5'})

    response = client.get(f'/game/{game_id}/state')
    assert response.status_code == 404


def test_real_state_rejects_unknown_game_id(client):
    response = client.get('/game/not-a-real-id/state')
    assert response.status_code == 404


def test_page_routes_for_test_and_game_namespaces(client):
    test_new_response = client.get('/test/new')
    assert test_new_response.status_code == 200

    test_game_id = _create_test_game(client, {'preset': '5'})
    test_page_response = client.get(f'/test/{test_game_id}')
    assert test_page_response.status_code == 200

    game_new_requires_login = client.get('/game/new', follow_redirects=False)
    assert game_new_requires_login.status_code == 302
    assert '/login' in game_new_requires_login.headers['Location']

    real_game_id = _create_real_game(client)
    real_game_response = client.get(f'/game/{real_game_id}')
    assert real_game_response.status_code == 200

    missing_game_response = client.get('/game/not-a-real-id')
    assert missing_game_response.status_code == 404


def test_legacy_new_game_route_redirects(client):
    response = client.get('/new-game', follow_redirects=False)
    assert response.status_code == 302
    assert '/game/new' in response.headers['Location']
