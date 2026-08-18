from flask import Flask, render_template, request, redirect, url_for, session, flash 
import pymysql, os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# DB 연결 함수
def db_connect():
    return pymysql.connect(
        host='127.0.0.1', 
        user='root',
        password=os.environ.get('DB_PASSWORD'),
        database='P4C_2_DB',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


# 메인 페이지
@app.route('/')
def index():
    conn = db_connect()
    curs = conn.cursor()
    sql = """
        SELECT p.id, p.title, u.username, p.created_at FROM posts p JOIN users u ON p.user_id = u.id ORDER BY p.id DESC
    """
    curs.execute(sql)
    posts = curs.fetchall()
    conn.close()

    return render_template('index.html', posts=posts)



# 회원가입 
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hash_pw = generate_password_hash(password)

        conn = db_connect()
        cursor = conn.cursor()

        try:
            sql = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
            cursor.execute(sql, (username, hash_pw))
            conn.commit()
            flash("회원가입이 완료되었습니다. 로그인해주세요.")
            return redirect(url_for('login'))
        except pymysql.err.IntegrityError:
            flash("이미 존재하는 ID입니다.")
        finally:
            conn.close()

    return render_template("signup.html")


# 로그인 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = db_connect()
        cursor = conn.cursor()

        sql = "SELECT * FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else :
            flash("아이디 또는 비밀번호가 올바르지 않습니다.")

    return render_template('login.html')


# 로그아웃
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# 게시글 작성
@app.route('/write', methods=['GET', 'POST'])
def write():
    if 'user_id' not in session:
        flash("로그인이 필요한 서비스입니다.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        conn = db_connect()
        cursor = conn.cursor()
        sql = "INSERT INTO posts (title, content, user_id) VALUES (%s, %s, %s)"
        cursor.execute(sql, (title, content, user_id))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('write.html')

# 게시글 열람
@app.route('/read/<int:id>')
def read(id):
    conn = db_connect()
    cursor = conn.cursor()
    sql = """
        SELECT p.id, p.title, p.content, p.created_at, u.username, p.user_id 
        FROM posts p JOIN users u ON p.user_id = u.id 
        WHERE p.id = %s
    """
    cursor.execute(sql, (id,))
    post = cursor.fetchone()
    conn.close()

    if not post:
        flash("존재하지 않는 게시글입니다.")
        return redirect(url_for('index'))

    return render_template('read.html', post=post)


# 게시글 삭제
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if 'user_id' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM posts WHERE id = %s", (id,))
    post = cursor.fetchone()

    if post and post['user_id'] == session['user_id']:
        cursor.execute("DELETE FROM posts WHERE id= %s", (id,))
        conn.commit()
        flash("게시물이 삭제되었습니다.")
    else:
        flash("게시물 삭제 권한이 없습니다.")

    conn.close()
    return redirect(url_for('index'))


# 회원 탈퇴
@app.route('/resign', methods=['POST'])
def resign():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM posts WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

    conn.commit()
    conn.close()

    session.clear()
    flash("회원 탈퇴가 완료되었습니다. 초기 화면으로 돌아갑니다.")

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=5001, debug=True)