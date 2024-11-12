import pytest
from ..app import app, db, User, Goal, Workout, Diet
from flask import session, url_for
from unittest.mock import patch, MagicMock
from datetime import datetime
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


    


def login(client, user_id):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id



def test_profile_logged_in(client):
    with app.app_context():
        # テスト用ユーザーを作成
        user = User(username="testuser", email="testuser@example.com", password="password")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        
        # サンプルデータの追加
        goal = Goal(user_id=user_id, target_calories=2000, target_workout_duration=60, target_date=datetime.today().date())
        workout = Workout(user_id=user_id, duration=30, date=datetime.today().date())
        diet = Diet(user_id=user_id, calories=1500, date=datetime.today().date())
        
        db.session.add_all([goal, workout, diet])
        db.session.commit()
        
        # ログイン状態での /profile アクセス
        login(client, user_id)
        response = client.get('/profile')
        
        # ステータスコードが200であることを確認
        assert response.status_code == 200
        
        # レンダリングされたHTMLに期待するデータが含まれているか確認
        assert b"testuser" in response.data
        assert b"2000" in response.data  # 目標摂取カロリー
        assert b"60" in response.data    # 目標運動時間
        assert b"1500" in response.data  # ダイエットデータのカロリー
        assert b"30" in response.data    # ワークアウトデータの運動時間



def test_profile_not_logged_in(client):
    # ログインしていない状態で /profile にアクセス
    response = client.get('/profile')
    
    # ログインページへのリダイレクトを確認
    assert response.status_code == 302
    assert '/login' in response.headers['Location']




def test_update_profile_logged_in(client):
    # アプリケーションコンテキスト内でデータベースの操作を行う
    with app.app_context():
        # テスト用のユーザーを作成
        user = User(username="testuser", email="testuser@example.com", password="password")
        db.session.add(user)
        db.session.commit()
        
        # ユーザーIDを取得
        user_id = user.id

    # セッションにユーザーIDを設定してログイン状態をシミュレーション
    with client.session_transaction() as session:
        session['user_id'] = user_id

    # プロフィール更新のテストデータをPOSTリクエストで送信
    response = client.post('/update_profile', data={
        'age': '25',
        'height': '175.5',
        'weight': '68.2'
    })

    # 更新後のページが正しく表示されるかを確認
    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"  # /profileへリダイレクトされるか
   

    # データベースの値が更新されているかを確認
    with app.app_context():
        updated_user = User.query.get(user_id)
        assert updated_user.age == 25
        assert updated_user.height == 175.5
        assert updated_user.weight == 68.2


def test_update_profile_not_logged_in(client):
    # ログインしていない状態で更新ページにアクセスするテスト
    response = client.get('/update_profile')
    
    # ログインページにリダイレクトされるか確認
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"  # /loginへリダイレクトされるか
