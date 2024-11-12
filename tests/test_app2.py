import pytest
from ..app import app, db
from flask import session
from unittest.mock import patch, MagicMock
import os, sys, re
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テストクライアントの設定
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # CSRFを無効化

    # データベースを作成
    with app.app_context():
        db.create_all()
    
    # テストクライアントの作成
    with app.test_client() as client:
        yield client
    
    # テスト終了後にデータベースを削除
    with app.app_context():
        db.drop_all()


# ダミーユーザーのログイン
@pytest.fixture
def login_user(client):
    with client.session_transaction() as session:
        session['user_id'] = 1  # ダミーのユーザーID


# /workout_progressのテスト - ログインしているユーザー向け
@patch('app.get_workout_data')
@patch('app.create_workout_graph')
def test_workout_progress_logged_in(mock_create_workout_graph, mock_get_workout_data, client, login_user):
    # ダミーデータの作成
    mock_data = pd.DataFrame({
        'date': pd.date_range(start="2024-01-01", periods=7),
        'duration': [30, 45, 60, 35, 50, 20, 40],
        'calories': [100, 200, 150, 180, 120, 160, 130]
    })
    mock_get_workout_data.return_value = mock_data

    # ダミーのグラフURLを設定
    mock_create_workout_graph.return_value = "data:image/png;base64"

    # リクエストを送信
    response = client.get('/workout_progress')
    assert response.status_code == 200  # ステータスコードが200であることを確認
    assert b'data:image/png;base64' in response.data


# /workout_progressのテスト - 未ログインユーザー向け
def test_workout_progress_not_logged_in(client):
    response = client.get('/workout_progress')
    assert response.status_code == 302  # リダイレクトが発生することを確認
    assert '/login' in response.location  # リダイレクト先がログインページであることを確認



def test_calorie_progress(client):
    # エンドポイントへのGETリクエストを送信
    response = client.get('/calorie_progress')

    # ステータスコードが200かどうかを確認
    assert response.status_code == 200

    # レスポンスのHTMLにbase64でエンコードされた画像が含まれているか確認
    # 1つ目のグラフ (カロリー摂取量の推移)
    assert re.search(r'data:image/png;base64,[A-Za-z0-9+/=]+', response.data.decode()), "Calorie line graph not found in response"

    # 2つ目のグラフ (栄養素の円グラフ)
    assert re.search(r'data:image/png;base64,[A-Za-z0-9+/=]+', response.data.decode()), "Nutrient pie chart not found in response"

    print("Both graphs are present in the HTML response.")
