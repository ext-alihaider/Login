from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import DictCursor
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your secret key'

# Database configuration
app.config['POSTGRES_HOST'] = '127.0.0.1'
app.config['POSTGRES_USER'] = 'postgres'
app.config['POSTGRES_PASSWORD'] = 'postgres'
app.config['POSTGRES_DB'] = 'test'

def get_db_connection():
    conn = psycopg2.connect(
        host=app.config['POSTGRES_HOST'],
        user=app.config['POSTGRES_USER'],
        password=app.config['POSTGRES_PASSWORD'],
        dbname=app.config['POSTGRES_DB']
    )
    return conn

def create_session(user_id, remote_addr, remote_host):
    session_key = str(uuid.uuid4())
    logged_in = datetime.now()
    session_expiry = logged_in + timedelta(minutes=30)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO login (user_id, session_key, remote_addr, remote_host, logged_in, session_expiry, status, origin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                   (user_id, session_key, remote_addr, remote_host, logged_in, session_expiry, 1, 1))
    conn.commit()
    cursor.close()
    conn.close()
    return session_key

def update_session(session_key):
    new_session_key = str(uuid.uuid4())
    session_expiry = datetime.now() + timedelta(minutes=30)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE login SET session_key = %s, session_expiry = %s WHERE session_key = %s',
                   (new_session_key, session_expiry, session_key))
    conn.commit()
    cursor.close()
    conn.close()
    return new_session_key

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session_key = create_session(account['id'], request.remote_addr, request.remote_host)
            session['session_key'] = session_key
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username/password!'
        cursor.close()
        conn.close()
    return render_template('index.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('session_key', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM login WHERE session_key = %s', (session['session_key'],))
        login_session = cursor.fetchone()
        if login_session and login_session['session_expiry'] > datetime.now():
            new_session_key = update_session(session['session_key'])
            session['session_key'] = new_session_key
            cursor.close()
            conn.close()
            return render_template('home.html', username=session['username'])
        else:
            cursor.close()
            conn.close()
            return redirect(url_for('logout'))
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
