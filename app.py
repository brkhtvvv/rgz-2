from flask import Flask, render_template, request, redirect
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Подключение к базе данных
def db_connect():
    conn = psycopg2.connect(
        host='olyabarkhatoova.mysql.pythonanywhere-services.com',
        database='olyabarkhatoova$default',
        user='olyabarkhatoova',
        password='1234'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cur

# Закрытие соединения с базой данных
def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()

# Главная страница: список пользователей
@app.route('/')
def index():
    conn, cur = db_connect()
    cur.execute('SELECT id, login, fullname, email, about FROM users')
    users = cur.fetchall()
    db_close(conn, cur)
    return render_template('index.html', users=users)

# Добавление нового пользователя
@app.route('/add', methods=['POST'])
def add_user():
    login = request.form.get('login')
    password = request.form.get('password')  # Пароль можно хэшировать
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    about = request.form.get('about')

    conn, cur = db_connect()
    cur.execute('''
        INSERT INTO users (login, password, fullname, email, about)
        VALUES (%s, %s, %s, %s, %s)
    ''', (login, password, fullname, email, about))
    db_close(conn, cur)

    return redirect('/')

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)
