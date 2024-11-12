import pytest
from ..app import app, db, User
import os
import sys
from flask import session, url_for
from werkzeug.security import generate_password_hash


# テスト用設定の作成
@pytest.fixture
def client():
    # テスト用にアプリケーションの設定を行う
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # データベースを作成
    with app.app_context():
        db.create_all()
    
    # テストクライアントの作成
    with app.test_client() as client:
        yield client
    
    # テスト終了後にデータベースを削除
    with app.app_context():
        db.drop_all()


### テストコード

# 登録のテスト
def test_register(client):
    # 新規ユーザーの登録データを送信
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'testpassword'
    })

    # リダイレクトを検証
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
    
    # データベースにユーザーが追加されたことを確認
    user = User.query.filter_by(email='testuser@example.com').first()
    assert user is not None
    assert user.username == 'testuser'


# ログインのテスト
def test_login(client):
    with app.app_context():
        # 事前にユーザーをデータベースに追加
        hashed_password = generate_password_hash('testpassword', method='pbkdf2:sha256')
        user = User(username='testuser', email='testuser@example.com', password=hashed_password)
        db.session.add(user)
        db.session.commit()

    # 正しい情報でログインを試行
    response = client.post('/login', data={
        'email': 'testuser@example.com',
        'password': 'testpassword'
    })

    assert response.status_code == 302  # リダイレクトを確認
    assert response.headers['Location'] == url_for('index')


# ログイン失敗のテスト
def test_login_fail(client):
    # 存在しないユーザーでログインを試行
    response = client.post('/login', data={
        'email': 'wronguser@example.com',
        'password': 'wrongpassword'
    })

    # エラーメッセージが表示されていることを確認
    assert response.status_code == 200
    assert "メールアドレスまたはパスワードが間違っています。".encode("utf-8") in response.data
