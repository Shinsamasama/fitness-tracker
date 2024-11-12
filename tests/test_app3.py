import pytest
from ..app import app, db, Goal, Diet, Workout, check_goal_progress
import os, sys
from datetime import datetime
from flask import session, url_for
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # CSRFを無効に

    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # テスト用のデータベースを作成
        yield client
        with app.app_context():
            db.drop_all()  # テスト後にデータベースを削除


def login(client, user_id):
    with client.session_transaction() as session:
        session['user_id'] = user_id


def test_set_goal_redirects_if_not_logged_in(client):
    response = client.post('/set_goal', data={
        'target_calories': '2000',
        'target_workout_duration': '60',
        'target_date': '2024-12-31'
    })
    # ログインしていない場合、ログインページにリダイレクトされることを確認
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_set_goal_sets_new_goal(client):
    # テストユーザーとしてログイン
    login(client, user_id=1)

    # POSTリクエストを送信して目標を設定
    response = client.post('/set_goal', data={
        'target_calories': '2000',
        'target_workout_duration': '60',
        'target_date': '2024-12-31'
    })
    
    # レスポンスの内容と目標が正しく設定されたかを確認
    assert response.status_code == 302
    assert response.headers['Location'] == url_for('index')

    # データベースを確認
    goal = Goal.query.filter_by(user_id=1).first()
    assert goal is not None
    assert goal.target_calories == 2000
    assert goal.target_workout_duration == 60
    assert goal.target_date.strftime('%Y-%m-%d') == '2024-12-31'

   



def test_set_goal_updates_existing_goal(client):
    # テストユーザーとしてログイン
    login(client, user_id=1)

    # 初回の目標設定
    client.post('/set_goal', data={
        'target_calories': '2000',
        'target_workout_duration': '60',
        'target_date': '2024-12-31'
    })
    
    # 目標を更新
    response = client.post('/set_goal', data={
        'target_calories': '1800',
        'target_workout_duration': '45',
        'target_date': '2024-11-30'
    })


    assert response.status_code == 302

    # データベースを確認
    goal = Goal.query.filter_by(user_id=1).first()
    assert goal is not None
    assert goal.target_calories == 1800
    assert goal.target_workout_duration == 45
    assert goal.target_date.strftime('%Y-%m-%d') == '2024-11-30'



def test_goal_progress_requires_login(client):
    # ログインしていない状態でのアクセスを確認
    response = client.get('/goal_progress')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_goal_progress_no_goal_set(client):
    # テストユーザーとしてログイン
    login(client, user_id=1)

    # 目標が設定されていない状態でのアクセスを確認
    response = client.get('/goal_progress')
    assert response.status_code == 302


def test_goal_progress_with_goal_set(client):
    # テストユーザーとしてログイン
    login(client, user_id=1)

    # テストデータの追加
    with app.app_context():
        # ユーザーの目標を設定
        goal = Goal(
            user_id=1, target_calories=2000, 
            target_workout_duration=60,
            target_date=datetime.strptime('2024-12-31', '%Y-%m-%d').date()  # 文字列を date オブジェクトに変換 
        )
        db.session.add(goal)
        
        # ダイエットと運動データを追加
        today = datetime.today().date()
        diet = Diet(user_id=1, calories=1500, date=today)
        workout = Workout(user_id=1, duration=30, date=today)
        db.session.add(diet)
        db.session.add(workout)
        db.session.commit()

    
        # 関数から達成率を取得
        progress = check_goal_progress(user_id=1)

        # 期待する達成率と一致するか確認
        assert progress["calorie_progress"] == 75  # 1500 / 2000 * 100
        assert progress["workout_progress"] == 50   # 30 / 60 * 100
    
