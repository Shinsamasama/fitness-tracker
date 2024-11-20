from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import io
import base64
from flask_migrate import Migrate


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "your_secret_key"   # フラッシュメッセージ用のシークレットキー

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ユーザーモデル
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    workouts = db.relationship('Workout', backref='user', lazy=True)
    diets = db.relationship('Diet', backref='user', lazy=True)


# ワークアウトモデル
class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    workout_type = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    calories = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 外部キーとしてuser_idを追加


# 食事モデル
class Diet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    food = db.Column(db.String(150))
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fat = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 外部キーとしてuser_idを追加


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_calories = db.Column(db.Float, nullable=False)
    target_workout_duration = db.Column(db.Integer, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    user = db.relationship('User', backref=db.backref('goals', lazy=True))


class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    criteria = db.Column(db.String(100))
    icon = db.Column(db.String(100))  # アイコンのパスやURL


class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    date_earned = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('user_badges', lazy=True))
    badge = db.relationship('Badge', backref=db.backref('user_badges', lazy=True))


class DailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    user = db.relationship('User', backref=db.backref('daily_tasks', lazy=True))


class TaskStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('daily_task.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)
    task = db.relationship('DailyTask', backref=db.backref('statuses', lazy=True))



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))



# 関数処理まとめ
@app.route('/log_workout', methods=['POST'])
def log_workout_route():
    workout_type = request.form['workout_type']
    duration = int(request.form['duration'])
    calories = float(request.form['calories'])
    user_id = session.get('user_id')

    # Workoutモデルを使って新しいレコードを追加
    new_workout = Workout(
        date=datetime.now().strftime('%Y-%m-%d'),
        workout_type=workout_type,
        duration=duration,
        calories=calories,
        user_id=user_id
    )

    db.session.add(new_workout)
    db.session.commit()
    flash("ワークアウトが記録されました", "success")
    return redirect(url_for('keep_record'))


@app.route('/log_diet', methods=['POST'])
def log_diet_route():
    food = request.form['food']
    calories = float(request.form['calories'])
    protein = float(request.form['protein'])
    carbs = float(request.form['carbs'])
    fat = float(request.form['fat'])
    user_id = session.get('user_id')

    # Dietモデルを使って新しいレコードを追加
    new_diet = Diet(
        date=datetime.now().strftime('%Y-%m-%d'),
        food=food,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        user_id=user_id
    )

    db.session.add(new_diet)
    db.session.commit()
    flash("食事が記録されました", "success")
    return redirect(url_for('keep_record'))


def get_workout_data(user_id):
    # SQLAlchemyクエリを使ってデータ取得
    workouts = Workout.query.filter_by(user_id=user_id).order_by(Workout.date).all()

    # データをDataFrameに変換
    data = [{'date': workout.date, 'duration': workout.duration, 'calories': workout.calories} for workout in workouts]
    df = pd.DataFrame(data)

    return df



# Aggバックエンドを使用してtkinterエラーを回避
matplotlib.use('Agg')

def create_workout_graph(df):
     # 日本語フォントの設定
    plt.rcParams['font.family'] = 'MS Gothic'
    plt.figure(figsize=(12, 6) )

    today = pd.to_datetime(datetime.today().date())
    start_date = today - timedelta(days=13)

    if df.empty:
        # データが空の場合、今日を基準に一週間の空データを作成
        today = pd.to_datetime(datetime.today().date())
        date_range = pd.date_range(start=today - timedelta(days=6), end=today)
        df = pd.DataFrame({'date': date_range, 'duration': [0] * 7, 'calories': [0] * 7})
    else:
        df['date'] = pd.to_datetime(df['date'])
        date_range = pd.date_range(start=start_date, end=today)
        df = df.groupby('date').sum().reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'duration', 'calories']

    
    # 日付を横軸に、運動時間と消費カロリーを縦軸にした折れ線グラフを作成
    plt.plot(df['date'], df['duration'], marker='o', color='b', label='運動時間(分)')
    plt.plot(df['date'], df['calories'], marker='x', color='r', label='消費カロリー(kcal)')

    plt.xlabel('日付', fontsize=12)
    plt.ylabel('値', fontsize=12)
    plt.title('運動時間と消費カロリーの推移', fontsize=16, fontweight='bold')

    # 日付を45度回転させる
    plt.xticks(df['date'], rotation=45)
    plt.legend(loc='upper left', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)

    # 最大値に注釈を追加
    max_duration = df['duration'].max()
    max_calories = df['calories'].max()
    max_duration_date = df.loc[df['duration'].idxmax(), 'date']
    max_calories_date = df.loc[df['calories'].idxmax(), 'date']

    plt.annotate(f'最大運動時間: {max_duration}分',
                xy=(max_duration_date, max_duration),
                xytext=(max_duration_date, max_duration + 10),
                arrowprops=dict(facecolor='#1f77b4', shrink=0.05),
                fontsize=10, color='#1f77b4')

    plt.annotate(f'最大消費カロリー: {max_calories}kcal',
                xy=(max_calories_date, max_calories),
                xytext=(max_calories_date, max_calories + 20),
                arrowprops=dict(facecolor='#ff7f0e', shrink=0.05),
                fontsize=10, color='#ff7f0e')

    plt.tight_layout()  # レイアウトを調整して、重なりを防ぐ

    # グラフを画像として保存し、base64エンコード
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{graph_url}"


def get_calorie_data():
    # セッションからユーザーIDを取得
    user_id = session.get('user_id')

    # Dietテーブルから該当ユーザーのデータを取得
    results = db.session.query(Diet.date, Diet.calories).filter_by(user_id=user_id).order_by(Diet.date).all()

    # データをDataFrameに変換
    df = pd.DataFrame(results, columns=['date', 'calories'])
    df['date'] = pd.to_datetime(df['date'])  # 日付をdatetime型に変換

    return df


def create_calorie_line_graph():
    plt.rcParams['font.family'] = 'MS Gothic'

    # データを取得
    df = get_calorie_data()

    # グラフの描画
    plt.figure(figsize=(12, 6))

    today = pd.to_datetime(datetime.today().date())
    start_date = today - timedelta(days=13)

    if df.empty:
        # データが空の場合、今日を基準に一週間の空データを生成
        today = pd.to_datetime(datetime.today().date())
        date_range = pd.date_range(start=today - timedelta(days=6), end=today)
        df = pd.DataFrame({'date': date_range, 'calories': [0] * 7})
    else:
        df['date'] = pd.to_datetime(df['date'])
        date_range = pd.date_range(start=start_date, end=today)
        df = df.groupby('date').sum().reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'calories']

    plt.plot(df['date'], df['calories'], marker='o', color='b', label='摂取カロリー(kcal)')

    plt.xlabel('日付', fontsize=12)
    plt.ylabel('カロリー(kcal)', fontsize=12)
    plt.title('摂取カロリーの推移', fontsize=16, fontweight='bold')

    plt.xticks(df['date'], rotation=45)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    max_calories = df['calories'].max()
    max_calories_date = df.loc[df['calories'].idxmax(), 'date']

    plt.annotate(f'最大摂取カロリー: {max_calories}kcal',
                xy=(max_calories_date, max_calories),
                xytext=(max_calories_date, max_calories + 10),
                arrowprops=dict(facecolor='blue', shrink=0.05),
                fontsize=10, color='blue')
    
    plt.tight_layout()

    # グラフを画像として保存し、base64でエンコード
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=100)
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{graph_url}"


def get_nutrient_data(user_id):
    # Dietテーブルから該当ユーザーの栄養素データを取得
    results = db.session.query(Diet.protein, Diet.fat, Diet.carbs).filter_by(user_id=user_id).all()

    # 各栄養素の総量を計算
    total_protein = sum([record.protein for record in results])
    total_fat = sum([record.fat for record in results])
    total_carbohydrate = sum([record.carbs for record in results])

    return total_protein, total_fat, total_carbohydrate


def create_nutrient_pie_chart():
    user_id = session.get('user_id')

    # 栄養素データを取得
    protein, fat, carbohydrate = get_nutrient_data(user_id)

    if protein == 0 and fat == 0 and carbohydrate == 0:
        calorie_data = [1] # ダミーのデータ
        labels = ['データなし']
        colors = ['#d3d3d3']
    else:
        # カロリーを計算
        protein_calories = protein * 4
        fat_calories = fat * 9
        carb_calories = carbohydrate * 4


        # カロリー比率をリスト化
        calorie_data = [protein_calories, fat_calories, carb_calories]
        labels = ['タンパク質', '脂質', '炭水化物']
        colors = ['#ff9999', '#66b3ff', '#99ff99']

    # 円グラフの作成
    plt.figure(figsize=(10, 10))
    plt.pie(calorie_data, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    plt.title("栄養素の割合表示")
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{graph_url}"


def check_goal_progress(user_id):
    # 最新の目標を取得
    goal = Goal.query.filter_by(user_id=user_id).order_by(Goal.target_date.desc()).first()
    if not goal:
        return None 
    
    # 記録データから期間内のカロリー摂取量と運動時間を計算
    total_calories = db.session.query(db.func.sum(Diet.calories)).filter_by(user_id=user_id).scalar() or 0
    total_duration = db.session.query(db.func.sum(Workout.duration)).filter_by(user_id=user_id).scalar() or 0

    # 目標達成率を計算
    calorie_progress = (total_calories / goal.target_calories) * 100 if goal.target_calories else 0
    workout_progress = (total_duration / goal.target_workout_duration) * 100 if goal.target_workout_duration else 0

    return {
        "calorie_progress": calorie_progress,
        "workout_progress": workout_progress
    }


def get_weekly_monthly_report(user_id):
    today = datetime.today().date()

    # 1週間前と1か月前の日付を取得
    week_ago = today - timedelta(weeks=1)
    month_ago = today - timedelta(days=30)

    # 1週間分のデータ
    weekly_workouts = Workout.query.filter(Workout.user_id == user_id, Workout.date >= week_ago).all()
    weekly_diets = Diet.query.filter(Diet.user_id == user_id, Diet.date >= week_ago).all()

    # 1か月分のデータ
    monthly_workouts = Workout.query.filter(Workout.user_id == user_id, Workout.date >= month_ago).all()
    monthly_diets = Diet.query.filter(Diet.user_id == user_id, Diet.date >= month_ago).all()

    # 集計（運動時間と摂取カロリー）
    weekly_report = {
        "total_workout_duration": sum([w.duration for w in weekly_workouts]),
        "total_calories": sum(d.calories for d in weekly_diets)
    }

    monthly_report = {
        "total_workout_duration": sum([w.duration for w in monthly_workouts]),
        "total_calories": sum(d.calories for d in monthly_diets)
    }

    return weekly_report, monthly_report


def create_report_graph(user_id, days):
    plt.rcParams['font.family'] = 'MS Gothic'
    
    # 日付の範囲
    today = datetime.today().date()
    start_date = today - timedelta(days=days)

    # データ取得: 運動時間と摂取カロリーの集計
    workouts = Workout.query.filter(Workout.user_id == user_id, Workout.date >= start_date).all()
    diets = Diet.query.filter(Diet.user_id == user_id, Diet.date >= start_date).all()

    # DataFrameに変換して日付ごとに集計
    workout_data = [{'date': workout.date, 'calories': workout.calories} for workout in workouts]
    diet_data = [{'date': diet.date, 'calories': diet.calories} for diet in diets]

    # 空のデータがある場合
    if not workout_data:
        df_workout = pd.DataFrame(columns=['date', 'calories'])
    else:
        df_workout = pd.DataFrame(workout_data).groupby('date').sum().reset_index()

    if not diet_data:
        df_diet = pd.DataFrame(columns=['date', 'calories'])
    else:
        df_diet = pd.DataFrame(diet_data).groupby('date').sum().reset_index()


    # 日付データをdatetime型に変換
    df_workout['date'] = pd.to_datetime(df_workout['date'], errors='coerce')
    df_diet['date'] = pd.to_datetime(df_diet['date'], errors='coerce')

    # NaTを削除
    df_workout = df_workout.dropna(subset=['date'])
    df_diet = df_diet.dropna(subset=['date'])
    

    # グラフの作成
    plt.figure(figsize=(12, 6))
    plt.plot(df_workout['date'], df_workout['calories'], marker='o', color='b', label='消費カロリー(kcal)')
    plt.plot(df_diet['date'], df_diet['calories'], marker='x', color='r', label='摂取カロリー(kcal)')
    
    # 軸ラベル、タイトル、グリッド
    plt.xlabel('日付')
    plt.ylabel('値')
    plt.title(f"{days}日間の消費カロリーと摂取カロリーの推移")
    plt.legend()
    plt.grid(True)
    plt.xticks(df_workout['date'], rotation=45) 

    # グラフを画像として保存しエンコード
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{graph_url}"


def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()


def check_goal_progress(user_id):
    # 最新の目標を取得
    goal = Goal.query.filter_by(user_id=user_id).order_by(Goal.target_date.desc()).first()
    if not goal:
        return None

    # 目標進歩計算
    total_calories = db.session.query(db.func.sum(Diet.calories)).filter_by(user_id=user_id).scalar() or 0
    total_duration = db.session.query(db.func.sum(Workout.duration)).filter_by(user_id=user_id).scalar() or 0

    calorie_progress = (total_calories / goal.target_calories) * 100 if goal.target_calories else 0
    workout_progress = (total_duration / goal.target_workout_duration) * 100 if goal.target_workout_duration else 0

    if calorie_progress >= 100:
        create_notification(user_id, "目標カロリー摂取量を達成しました!")
    if workout_progress >= 100:
        create_notification(user_id, "目標運動時間を達成しました!")

    return {
        "calorie_progress": calorie_progress,
        "workout_progress": workout_progress
    }


def check_reminder_notifications(user_id):
    user = User.query.get(user_id)
    today = datetime.today().date()

    # 運動リマインド
    last_workout = Workout.query.filter_by(user_id=user_id).order_by(Workout.date.desc()).first()
    if not last_workout or (today - last_workout.date).days >= 7:
        create_notification(user_id, "1週間以上運動をしていません。運動を記録しましょう!")

    # 食事リマインド
    last_diet = Diet.query.filter_by(user_id=user_id).order_by(Diet.date.desc()).first()
    if not last_diet or (today - last_diet.date).days >= 1:
        create_notification(user_id, "今日の食事がまだ記録されていません。食事を記録しましょう！")

    # 目標未達成リマインド
    goal = Goal.query.filter_by(user_id=user_id).order_by(Goal.target_date.desc()).first()
    if goal and goal.target_date > today:
        progress = check_goal_progress(user_id)
        if progress['calorie_progress'] < 50 or progress['workout_progress'] < 50:
            create_notification(user_id, "目標達成まで半分以上の進歩が必要です。頑張りましょう!")

    db.session.commit()


def check_and_award_badges(user_id):
    user = User.query.get(user_id)

    # 運動10日連続バッジチェック
    workouts = Workout.query.filter_by(user_id=user_id).order_by(Workout.date.desc()).limit(10).all()
    if len(workouts) == 10:
        add_badge_to_user(user_id, "10日連続運動バッジ")

def add_badge_to_user(user_id, badge_name):
    badge = Badge.query.filter_by(name=badge_name).first()
    if badge:
        user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
        db.session.add(user_badge)
        db.session.commit()


def notify_new_badge(user_id, badge_name):
    message = f"新しいバッジ「{badge_name}」を獲得しました！"
    create_notification(user_id, message)


def get_today_progress(user_id):
    today = datetime.today().date()

    # 今日の運動時間の合計
    total_workout_duration = db.session.query(db.func.sum(Workout.duration)).filter(Workout.user_id == user_id,
    Workout.date == today).scalar() or 0

    # 今日の摂取カロリーの合計
    total_calories = db.session.query(db.func.sum(Diet.calories)).filter(Diet.user_id == user_id,
    Diet.date == today).scalar() or 0

    # ユーザーの最新目標を取得
    goal = Goal.query.filter_by(user_id=user_id).order_by(Goal.target_date.desc()).first()

    # 今日の進捗状況（目標に対する割合）を計算
    calorie_progress = (total_calories / goal.target_calories) * 100 if goal and goal.target_calories else 0
    workout_progress = (total_workout_duration / goal.target_workout_duration) * 100 if goal and goal.target_workout_duration else 0
    
    return {
        "total_workout_duration": total_workout_duration,
        "total_calories": total_calories,
        "calorie_progress": calorie_progress,
        "workout_progress": workout_progress
    }


def calculate_calories(activity_type, duration, weight):
    MET_values = {
        'walking': 3.5,
        'running': 7.0,
        'cycling': 4.0,
        'hard_working_out': 7.0,
        'light_working_out': 5.0

    }

    met = MET_values.get(activity_type, 1)
    return met * weight * (duration / 60)



    






# Flaskアプリのルート設定
@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        # 新しいユーザーの作成
        new_user = User(username=username, email=email, password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            db.session.rollback()  # エラー時にロールバック
            flash("このユーザー名またはメールアドレスはすでに登録されています。", "danger")

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # SQLAlchemyでユーザー情報を取得
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # セッションにユーザーIDを保存
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash("メールアドレスまたはパスワードが間違っています。", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    # セッションからユーザー情報を削除
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/keep_record')
def keep_record():
    return render_template('keep_record.html')


@app.route('/workout_progress')
def workout_progress():
    # ユーザーがログインしてるか確認
    if 'user_id' not in session:
        flash("ログインしてください", "warning")
        return redirect(url_for('login'))

    # 運動データを取得
    user_id = session['user_id']
    df = get_workout_data(user_id)

    # グラフの作成
    graph_url = create_workout_graph(df)

    return render_template('workout_progress.html', graph_url=graph_url)


@app.route('/calorie_progress')
def calorie_progress():
    # グラフ画像のURLを取得
    graph_url = create_calorie_line_graph()
    graph_url2 = create_nutrient_pie_chart()

    return render_template('calorie_progress.html', graph_url=graph_url, graph_url2=graph_url2)


@app.route('/set_goal', methods=['GET', 'POST'])
def set_goal():
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            flash("ログインが必要です。", "warning")
            return redirect(url_for('login'))
        
        # フォームデータを取得
        target_calories = float(request.form['target_calories'])
        target_workout_duration = int(request.form['target_workout_duration'])
        target_date = datetime.strptime(request.form['target_date'], '%Y-%m-%d').date()

        # ユーザーの既存目標を取得
        goal = Goal.query.filter_by(user_id=user_id).first()

        if goal:
            # 既存の目標があれば更新
            goal.target_calories = target_calories
            goal.target_workout_duration = target_workout_duration
            goal.target_date = target_date
            flash("目標が更新されました!", "success")
        else:
            new_goal = Goal(
                user_id = user_id,
                target_calories = target_calories,
                target_workout_duration = target_workout_duration,
                target_date = target_date
            )

            db.session.add(new_goal)
            flash("目標が設定されました!", "success")

        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('set_goal.html')


@app.route('/goal_progress')
def goal_progress():
    user_id = session.get('user_id')
    if not user_id:
        flash("ログインが必要です", "warning")
        return redirect(url_for('login'))
    
    # 目標達成率を取得
    progress = check_goal_progress(user_id)

    if not progress:
        flash("目標が設定されていません。", "info")
        return redirect(url_for('set_goal'))
    
    return render_template('goal_progress.html', progress=progress)


@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("ログインが必要です。", "warning")
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        user.age = int(request.form['age']) if request.form['age'] else None
        user.height = float(request.form['height']) if request.form['height'] else None
        user.weight = float(request.form['weight']) if request.form['weight'] else None

        db.session.commit()
        flash("プロフィールが更新されました!", "success")
        return redirect(url_for('profile'))
    
    return render_template('update_profile.html', user=user)


@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("ログインが必要です。", "warning")
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    goals = Goal.query.filter_by(user_id=user_id).order_by(Goal.target_date.desc()).first()
    workouts = Workout.query.filter_by(user_id=user_id).all()
    diets = Diet.query.filter_by(user_id=user_id).all()

    return render_template('profile.html', user=user, goal=goals, workouts=workouts, diets=diets)


@app.route('/index')
def index():
    user_id = session.get('user_id')

    if not user_id:
        flash("ログインが必要です。", "warning")
        return redirect(url_for('login'))
    
    user = User.query.filter_by(id=user_id).first()
    
    # 週間、月間レポートを取得
    weekly_report, monthly_report = get_weekly_monthly_report(user_id)

    # 週間と月間のグラフ画像URLを取得
    weekly_graph_url = create_report_graph(user_id, days=7)
    monthly_graph_url = create_report_graph(user_id, days=30)

    # 今日の進歩状況を取得
    today_progress = get_today_progress(user_id) if get_today_progress(user_id) else {}

    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()

   

    return render_template('index.html',
                           user = user, 
                           weekly_report=weekly_report, 
                           monthly_report=monthly_report,
                           weekly_graph_url=weekly_graph_url,
                           monthly_graph_url=monthly_graph_url,
                           today_progress=today_progress,
                           notifications=notifications
                        )


@app.route('/add_task', methods=['POST'])
def add_task():
    user_id = session.get('user_id')
    task_name = request.form['task_name']
    new_task = DailyTask(user_id=user_id, task_name=task_name)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    task = DailyTask.query.get(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/update_task_status', methods=['POST'])
def update_task_status():
    task_id = request.form['task_id']
    is_completed = request.form['is_completed'] == 'true'
    today = datetime.utcnow().date()

    # 今日の完了状況を取得か作成
    status = TaskStatus.query.filter_by(task_id=task_id, date=today).first()
    if not status:
        status = TaskStatus(task_id=task_id, date=today, is_completed=is_completed)
        db.session.add(status)
    else:
        status.is_completed = is_completed
    db.session.commit()

    return '', 204  # 成功リスポンスを返す


@app.route('/notifications')
def notifications():
    user_id = session.get('user_id')
    if not user_id:
        flash("ログインしてください", "warning")
        return redirect(url_for('login'))

    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.created_at.desc()).all()
    return render_template('index.html', notifications=notifications)


@app.route('/mark_notifications_as_read', methods=['POST'])
def mark_notifications_as_read():
    user_id = session.get('user_id')
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('notifications'))






if __name__ == '__main__':
    app.run(debug=True)