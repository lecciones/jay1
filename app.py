from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from functools import wraps
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"
DB = "tasks.db"

# ---------------- Database Initialization ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )''')
    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    due_date TEXT,
                    due_time TEXT,
                    priority TEXT DEFAULT 'Normal',
                    status TEXT DEFAULT 'Pending',
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')
    conn.commit()
    conn.close()

# ---------------- Query Helper ----------------
def query_db(query, args=(), one=False):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

# ---------------- Login Required Decorator ----------------
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

# ---------------- Routes ----------------

@app.route('/')
def homepage():
    return render_template("homepage.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if not username or not password:
            flash("All fields required", "warning")
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        try:
            with sqlite3.connect(DB) as con:
                con.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed_pw))
            flash("User registered! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        user = query_db("SELECT * FROM users WHERE username=?", [username], one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Logged in successfully", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('homepage'))

# ---------------- Task Routes ----------------

@app.route('/index')
@login_required
def index():
    user_id = session['user_id']
    tasks = query_db("SELECT * FROM tasks WHERE user_id=?", [user_id])
    today = date.today().isoformat()
    return render_template("index.html", tasks=tasks, now_date=today)

@app.route('/add', methods=['GET','POST'])
@login_required
def add():
    if request.method == 'POST':
        user_id = session['user_id']
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        category = request.form.get('category','').strip()
        due_date = request.form.get('due_date','').strip()
        due_time = request.form.get('due_time','').strip()
        priority = request.form.get('priority','Normal')
        if not title:
            flash("Title is required", "warning")
            return redirect(url_for('add'))
        with sqlite3.connect(DB) as con:
            con.execute("""INSERT INTO tasks 
                        (user_id,title,description,category,due_date,due_time,priority)
                        VALUES (?,?,?,?,?,?,?)""",
                        (user_id,title,description,category or None,due_date or None,due_time or None,priority))
        flash("Task added", "success")
        return redirect(url_for('index'))
    return render_template("form.html", action="Add", task=None)

@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    task = query_db("SELECT * FROM tasks WHERE id=? AND user_id=?", (id, session['user_id']), one=True)
    if not task:
        flash("Task not found", "danger")
        return redirect(url_for('index'))
    if request.method=='POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        category = request.form.get('category','').strip()
        due_date = request.form.get('due_date','').strip()
        due_time = request.form.get('due_time','').strip()
        priority = request.form.get('priority','Normal')
        status = request.form.get('status','Pending')
        if not title:
            flash("Title is required", "warning")
            return redirect(url_for('edit',id=id))
        with sqlite3.connect(DB) as con:
            con.execute("""UPDATE tasks SET title=?, description=?, category=?, due_date=?, due_time=?, priority=?, status=? WHERE id=?""",
                        (title, description, category or None, due_date or None, due_time or None, priority, status, id))
        flash("Task updated", "success")
        return redirect(url_for('index'))
    return render_template("form.html", action="Edit", task=task)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (id, session['user_id']))
    flash("Task deleted", "info")
    return redirect(url_for('index'))

@app.route('/complete/<int:id>', methods=['POST'])
@login_required
def complete(id):
    with sqlite3.connect(DB) as con:
        con.execute("UPDATE tasks SET status='Completed' WHERE id=? AND user_id=?", (id, session['user_id']))
    flash("Task marked as completed", "success")
    return redirect(url_for('index'))

# ---------------- Run App ----------------
if __name__=='__main__':
    init_db()
    app.run(debug=True)
