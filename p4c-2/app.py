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

    keyword = request.args.get('keyword', '')
    search_type = request.args.get('search_type', 'all')

    common_sql = """
        SELECT p.id, p.title, u.username, p.created_at, p.updated_at FROM posts p JOIN users u ON p.user_id = u.id 
    """

    if keyword:
        search_word = f"%{keyword}%"
        if search_type == 'title':
            sql = common_sql + "WHERE p.title LIKE %s ORDER BY p.id DESC"
            curs.execute(sql, (search_word,))
        elif search_type == 'content':
            sql = common_sql + "WHERE p.content LIKE %s ORDER BY p.id DESC"
            curs.execute(sql, (search_word, ))
        else:
            sql = common_sql + "WHERE p.title LIKE %s OR p.content LIKE %s ORDER BY p.id DESC"
            curs.execute(sql, (search_word, search_word))
    else:
        sql = common_sql + "ORDER BY p.id DESC"
        curs.execute(sql)

    posts = curs.fetchall()
    conn.close()

    return render_template('index.html', posts=posts, keyword=keyword, search_type=search_type)



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
        if len(title) > 100:
            return "<script>alert('제목은 100자를 초과할 수 없습니다.'); history.back();</script>"
        elif len(content) > 5000:
            return "<script>alert('본문은 5000자를 초과할 수 없습니다.'); history.back();</script>"

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
    sql_post = """
        SELECT p.*, u.username
        FROM posts p JOIN users u ON p.user_id = u.id 
        WHERE p.id = %s
    """
    cursor.execute(sql_post, (id,))
    post = cursor.fetchone()

    if not post:
        conn.close()
        flash("존재하지 않는 게시글입니다.")
        return redirect(url_for('index'))

    sql_comments = "SELECT * FROM comments WHERE post_id = %s ORDER BY created_at ASC"
    cursor.execute(sql_comments, (id,))
    comments = cursor.fetchall()
    conn.close()

    return render_template('read.html', post=post, comments=comments)

# 게시글 수정
@app.route('/modify/<int:id>', methods=['GET','POST'])
def modify(id):
    if 'user_id' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM posts WHERE id = %s", (id,))
    post = cursor.fetchone()

    if not post or post['user_id'] != session['user_id']:
        flash("권한이 없거나 존재하지 않는 게시물입니다.")
        conn.close()
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if len(title) > 100:
            return "<script>alert('제목은 100자를 초과할 수 없습니다.'); history.back();</script>"
        elif len(content) > 5000:
            return "<script>alert('본문은 5000자를 초과할 수 없습니다.'); history.back();</script>"

        sql = "UPDATE posts SET title = %s, content = %s WHERE id = %s"
        cursor.execute(sql, (title, content, id))
        conn.commit()
        conn.close()
        return redirect(url_for('read', id=id))
    conn.close()
    return render_template('modify.html', post=post)



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


# 댓글 저장
@app.route('/comment', methods=['POST'])
def comment():
    if not session.get('user_id'):
        flash('로그인이 필요한 기능입니다.')
        return redirect(url_for('login'))
    
    post_id = request.form.get('post_id')
    username = session.get('username')
    content = request.form.get('content')

    if not content or len(content.strip()) == 0:
        flash('댓글 내용을 입력해주세요.')
        return redirect(url_for('read', id=post_id))

    if len(content) > 1000:
        flash('댓글은 1000자를 초과할 수 없습니다.')
        return redirect(url_for('read', id=post_id))

    conn = db_connect()
    cursor = conn.cursor()
    sql = "INSERT INTO comments (post_id, username, content) VALUES (%s, %s, %s)"
    cursor.execute(sql, (post_id, username, content))

    conn.commit()
    conn.close()

    return redirect(url_for('read', id=post_id))


if __name__ == '__main__':
    app.run(port=5001, debug=True)  