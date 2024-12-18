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
    try:
        conn, cur = db_connect()
        # Если пользователь авторизован, показываем email авторов
        if 'user_id' in session:
            cur.execute("""
                SELECT ads.id, ads.title, ads.content, users.fullname AS author, users.email
                FROM ads
                JOIN users ON ads.user_id = users.id;
            """)
        else:
            cur.execute("""
                SELECT ads.id, ads.title, ads.content, users.fullname AS author
                FROM ads
                JOIN users ON ads.user_id = users.id;
            """)
        ads = cur.fetchall()
        db_close(conn, cur)
        return render_template('index.html', ads=ads)
    except Exception as e:
        return f"An error occurred: {str(e)}"







@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form['login']
        password = generate_password_hash(request.form['password'])
        fullname = request.form['fullname']
        email = request.form['email']
        about = request.form.get('about', '')
        avatar = request.files['avatar']

        filename = secure_filename(avatar.filename)
        avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn, cur = db_connect()
        cur.execute("INSERT INTO users (login, password, fullname, email, about, avatar) VALUES (%s, %s, %s, %s, %s, %s);",
                    (login, password, fullname, email, about, filename))
        db_close(conn, cur)

        # Перенаправляем на главную страницу после регистрации
        return redirect(url_for('main'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        conn, cur = db_connect()
        try:
            # Выполняем запрос для получения пользователя по логину
            cur.execute("SELECT * FROM users WHERE login=%s;", (login,))
            user = cur.fetchone()
            db_close(conn, cur)

            # Проверяем, если пользователь найден и пароль правильный
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['is_admin'] = user.get('is_admin', False)  # Понимание, есть ли поле is_admin
                return redirect(url_for('main'))
            else:
                return render_template('login.html', error='Invalid credentials')
        except Exception as e:
            db_close(conn, cur)
            return render_template('login.html', error=f"Error: {str(e)}")
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()  # Очищаем сессию
    return redirect(url_for('main'))



# ----------------------- Admin Management ------------------------
@jsonrpc.method('admin.delete_user')
def delete_user(user_id: int):
    if not session.get('is_admin'):
        return {'error': 'Unauthorized'}
    conn, cur = db_connect()
    cur.execute("DELETE FROM users WHERE id=%s;", (user_id,))
    db_close(conn, cur)
    return {'success': 'User deleted'}

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/ads')
def ads():
    try:
        # Подключаемся к базе данных
        conn, cur = db_connect()

        # Выполняем SQL-запрос для получения списка объявлений и данных об авторах
        cur.execute("""
            SELECT ads.id, ads.title, ads.content, users.fullname AS author, users.email
            FROM ads
            JOIN users ON ads.user_id = users.id;
        """)
        ads = cur.fetchall()

        # Закрываем соединение с базой данных
        db_close(conn, cur)

        # Передаем данные в шаблон
        return render_template('ads.html', ads=ads)

    except Exception as e:
        print(f"Error fetching ads: {e}")
        return "Internal Server Error", 500



@app.route('/create_ad', methods=['GET', 'POST'])
def create_ad():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        conn, cur = db_connect()
        cur.execute("INSERT INTO ads (title, content, user_id) VALUES (%s, %s, %s);", (title, content, user_id))
        db_close(conn, cur)
        return redirect(url_for('profile'))

    return render_template('create_ad.html')




@app.route('/edit_ad/<int:ad_id>', methods=['GET', 'POST'])
def edit_ad(ad_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn, cur = db_connect()
    cur.execute("SELECT * FROM ads WHERE id=%s;", (ad_id,))
    ad = cur.fetchone()

    if ad is None or ad['user_id'] != session['user_id']:
        return redirect(url_for('main'))  # Если это не ваше объявление, перенаправляем

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # Обновляем существующее объявление
        cur.execute("UPDATE ads SET title=%s, content=%s WHERE id=%s;", (title, content, ad_id))
        db_close(conn, cur)
        return redirect(url_for('profile'))  # Перенаправляем на страницу профиля после обновления

    db_close(conn, cur)
    return render_template('edit_ad.html', ad=ad)





@app.route('/delete_ad/<int:ad_id>', methods=['POST'])
def delete_ad(ad_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn, cur = db_connect()
    cur.execute("SELECT * FROM ads WHERE id=%s;", (ad_id,))
    ad = cur.fetchone()

    if ad is None or ad['user_id'] != session['user_id']:
        return redirect(url_for('main'))

    cur.execute("DELETE FROM ads WHERE id=%s;", (ad_id,))
    db_close(conn, cur)
    return redirect(url_for('profile'))



@jsonrpc.method('ad.create')
def create_ad_rpc(title: str, content: str):
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}
    
    user_id = session['user_id']
    conn, cur = db_connect()
    cur.execute("INSERT INTO ads (title, content, user_id) VALUES (%s, %s, %s);", (title, content, user_id))
    db_close(conn, cur)
    return {'success': 'Ad created'}

@jsonrpc.method('ad.edit')
def edit_ad_rpc(ad_id: int, title: str, content: str):
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}
    
    conn, cur = db_connect()
    cur.execute("SELECT * FROM ads WHERE id=%s;", (ad_id,))
    ad = cur.fetchone()

    if ad is None or ad['user_id'] != session['user_id']:
        return {'error': 'Unauthorized'}

    cur.execute("UPDATE ads SET title=%s, content=%s WHERE id=%s;", (title, content, ad_id))
    db_close(conn, cur)
    return {'success': 'Ad updated'}

@jsonrpc.method('ad.delete')
def delete_ad_rpc(ad_id: int):
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}
    
    conn, cur = db_connect()
    cur.execute("SELECT * FROM ads WHERE id=%s;", (ad_id,))
    ad = cur.fetchone()

    if ad is None or ad['user_id'] != session['user_id']:
        return {'error': 'Unauthorized'}

    cur.execute("DELETE FROM ads WHERE id=%s;", (ad_id,))
    db_close(conn, cur)
    return {'success': 'Ad deleted'}

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        print("User not logged in")
        return redirect(url_for('login'))

    conn, cur = db_connect()
    
    # Получаем информацию о пользователе
    cur.execute("SELECT * FROM users WHERE id=%s;", (session['user_id'],))
    user = cur.fetchone()

    # Получаем все объявления текущего пользователя
    cur.execute("""
        SELECT * FROM ads WHERE user_id=%s;
    """, (session['user_id'],))
    ads = cur.fetchall()

    db_close(conn, cur)

    if user:
        return render_template('profile.html', user=user, ads=ads)
    else:
        print("User not found in database")
        return redirect(url_for('login'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn, cur = db_connect()
    cur.execute("SELECT * FROM users WHERE id=%s;", (session['user_id'],))
    user = cur.fetchone()

    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        about = request.form.get('about', '')
        avatar = request.files.get('avatar')

        # Обновление данных
        if avatar:
            filename = secure_filename(avatar.filename)
            avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur.execute("UPDATE users SET fullname=%s, email=%s, about=%s, avatar=%s WHERE id=%s;",
                        (fullname, email, about, filename, session['user_id']))
        else:
            cur.execute("UPDATE users SET fullname=%s, email=%s, about=%s WHERE id=%s;",
                        (fullname, email, about, session['user_id']))

        db_close(conn, cur)
        return redirect(url_for('profile'))

    db_close(conn, cur)
    return render_template('edit_profile.html', user=user)

@app.route('/users')
def users():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('main'))  # Только администратор может видеть этот список

    try:
        conn, cur = db_connect()
        cur.execute("SELECT * FROM users;")
        users = cur.fetchall()
        db_close(conn, cur)
        return render_template('users.html', users=users)
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('main'))  # Только администратор может удалять пользователей

    try:
        conn, cur = db_connect()
        cur.execute("DELETE FROM users WHERE id=%s;", (user_id,))
        db_close(conn, cur)
        return redirect(url_for('users'))
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('main'))  # Только администратор может редактировать пользователей

    conn, cur = db_connect()
    cur.execute("SELECT * FROM users WHERE id=%s;", (user_id,))
    user = cur.fetchone()

    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        about = request.form.get('about', '')
        avatar = request.files.get('avatar')

        # Обновление данных пользователя
        if avatar:
            filename = secure_filename(avatar.filename)
            avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur.execute("UPDATE users SET fullname=%s, email=%s, about=%s, avatar=%s WHERE id=%s;",
                        (fullname, email, about, filename, user_id))
        else:
            cur.execute("UPDATE users SET fullname=%s, email=%s, about=%s WHERE id=%s;",
                        (fullname, email, about, user_id))

        db_close(conn, cur)
        return redirect(url_for('users'))  # После редактирования возвращаем на страницу пользователей

    db_close(conn, cur)
    return render_template('edit_user.html', user=user)

@app.route('/delete_ad_admin/<int:ad_id>', methods=['POST'])
def delete_ad_admin(ad_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Пользователь должен быть авторизован

    try:
        conn, cur = db_connect()
        
        # Проверяем, администратор ли пользователь
        is_admin = session.get('is_admin', False)
        
        if is_admin:
            # Администратор может удалить любое объявление
            cur.execute("DELETE FROM ads WHERE id=%s;", (ad_id,))
        else:
            db_close(conn, cur)
            return redirect(url_for('main'))  # Если пользователь не администратор, перенаправляем

        db_close(conn, cur)
        return redirect(url_for('main'))  # Перенаправляем на главную страницу после удаления
    except Exception as e:
        return f"An error occurred: {str(e)}"
