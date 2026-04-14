import pytest

from app import create_app, db
from app.models import Account
from config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret'


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / 'satura-test.db'

    class LocalTestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

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
    response = client.post('/game', json={})
    assert response.status_code == 201
    game_id = response.get_json()['game_id']
    assert game_id
    return game_id


def test_settings_requires_login(client):
    response = client.get('/settings/profile', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_settings_pages_load_after_login(client):
    _login(client)
    for path in (
        '/settings/profile',
        '/settings/account',
        '/settings/game',
        '/settings/feedback',
        '/settings/about-legal',
    ):
        response = client.get(path)
        assert response.status_code == 200


def test_nav_profile_icon_links_to_settings(client):
    _login(client)
    response = client.get('/')
    html = response.get_data(as_text=True)
    assert '/settings/profile' in html
    assert 'nav-dropdown' not in html


def test_settings_game_defaults_persist(client, app):
    _login(client)
    response = client.post('/settings/game', data={
        'action': 'save_defaults',
        'time_control': 'custom',
        'custom_minutes': '22',
        'default_player': 'p2',
        'default_board_size': '23',
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/settings/game#defaults')

    with app.app_context():
        user = Account.query.filter_by(username='P1_Test').first()
        assert user is not None
        assert user.settings is not None
        assert user.settings.default_time_control == 'custom'
        assert user.settings.custom_minutes == 22
        assert user.settings.default_player == 'p2'
        assert user.settings.default_board_size == 24


def test_account_delete_anonymizes_and_flags(client, app):
    _login(client)

    response = client.post('/settings/account', data={
        'action': 'delete_account',
        'confirm_username': 'P1_Test',
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.headers['Location']

    with app.app_context():
        user = Account.query.filter_by(id=1).first()
        assert user is not None
        assert user.deleted is True
        assert user.disabled is True
        assert user.email is None
        assert user.username.startswith(Config.DELETED_USERNAME)


def test_legacy_profile_account_settings_endpoints_removed(client):
    _login(client)
    for path in ('/profile', '/account', '/settings'):
        response = client.get(path)
        assert response.status_code == 404


def test_profile_recent_games_matches_my_games_timeline_and_limits_to_four(client):
    _login(client)
    created_ids = [_create_game(client) for _ in range(5)]
    expected_ids = created_ids[-4:]

    response = client.get('/settings/profile')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert html.count('class="game-timeline-row"') == 4
    assert html.count('href="/my-games/') == 4
    for game_id in expected_ids:
        assert f'href="/my-games/{game_id}"' in html
    assert f'href="/my-games/{created_ids[0]}"' not in html
    assert 'href="/my-games"' in html
    assert 'Show more' in html
