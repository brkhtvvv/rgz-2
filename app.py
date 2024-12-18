from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jsonrpc import JSONRPC
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key'
jsonrpc = JSONRPC(app, '/api')
UPLOAD_FOLDER = 'static/avatars'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database connection
def db_connect():
    conn = psycopg2.connect(
        host='127.0.0.1',
        database='olga_barkhatova_knowledge_bace',
        user='olga_barkhatova_knowledge_bace',
        password='123'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cur

def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()

# ----------------------- User Routes ------------------------
@app.route('/')
def main():
    conn, cur = db_connect()
    cur.execute("SELECT posts.id, posts.title, posts.content, users.name AS author FROM posts JOIN users ON posts.user_id = users.id;")
    posts = cur.fetchall()
    db_close(conn, cur)
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = generate_password_hash(request.form['password'])
        name = request.form['name']
        email = request.form['email']
        about = request.form.get('about', '')
        avatar = request.files['avatar']

        filename = secure_filename(avatar.filename)
        avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn, cur = db_connect()
        cur.execute("INSERT INTO users (login, password, name, email, about, avatar) VALUES (%s, %s, %s, %s, %s, %s);",
                    (login, password, name, email, about, filename))
        db_close(conn, cur)
        return redirect(url_for('main'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        conn, cur = db_connect()
        cur.execute("SELECT * FROM users WHERE login=%s;", (login,))
        user = cur.fetchone()
        db_close(conn, cur)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('main'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main'))

# ----------------------- Post Management ------------------------
@jsonrpc.method('post.create')
def create_post(title: str, content: str):
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}
    conn, cur = db_connect()
    cur.execute("INSERT INTO posts (title, content, user_id) VALUES (%s, %s, %s);",
                (title, content, session['user_id']))
    db_close(conn, cur)
    return {'success': 'Post created'}

@jsonrpc.method('post.edit')
def edit_post(post_id: int, title: str, content: str):
    conn, cur = db_connect()
    cur.execute("UPDATE posts SET title=%s, content=%s WHERE id=%s AND user_id=%s;",
                (title, content, post_id, session['user_id']))
    db_close(conn, cur)
    return {'success': 'Post updated'}

@jsonrpc.method('post.delete')
def delete_post(post_id: int):
    conn, cur = db_connect()
    cur.execute("DELETE FROM posts WHERE id=%s AND user_id=%s;", (post_id, session['user_id']))
    db_close(conn, cur)
    return {'success': 'Post deleted'}

# ----------------------- Admin Management ------------------------
@jsonrpc.method('admin.delete_user')
def delete_user(user_id: int):
    if not session.get('is_admin'):
        return {'error': 'Unauthorized'}
    conn, cur = db_connect()
    cur.execute("DELETE FROM users WHERE id=%s;", (user_id,))
    db_close(conn, cur)
    return {'success': 'User deleted'}

@jsonrpc.method('admin.delete_post')
def admin_delete_post(post_id: int):
    if not session.get('is_admin'):
        return {'error': 'Unauthorized'}
    conn, cur = db_connect()
    cur.execute("DELETE FROM posts WHERE id=%s;", (post_id,))
    db_close(conn, cur)
    return {'success': 'Post deleted'}

if __name__ == '__main__':
    app.run(debug=True)
