from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"

DB = "tasks.db"

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    reminder_date TEXT,
                    reminder_time TEXT,
                    done INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()


def query_db(query, args=(), one=False):
    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

@app.route('/')
def index():

    cat = request.args.get('category')
    status = request.args.get('status')
    order = request.args.get('order', 'due_date') 

    base = "SELECT * FROM tasks"
    conditions = []
    params = []

    if cat:
        conditions.append("category = ?")
        params.append(cat)
    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        base += " WHERE " + " AND ".join(conditions)

    if order == 'priority':
        base += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Normal' THEN 2 ELSE 3 END, due_date"
    else:
        base += " ORDER BY due_date IS NULL, due_date" 

    tasks = query_db(base, params)
 
    categories = query_db("SELECT DISTINCT category FROM tasks WHERE category IS NOT NULL AND category <> ''")
    return render_template("index.html", tasks=tasks, categories=categories)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        category = request.form.get('category','').strip()
        due_date = request.form.get('due_date','').strip() 
        priority = request.form.get('priority','Normal')
        if not title:
            flash("Title is required", "warning")
            return redirect(url_for('add'))
        with sqlite3.connect(DB) as con:
            con.execute("""
                INSERT INTO tasks (title, description, category, due_date, priority)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, category or None, due_date or None, priority))
        flash("Task added", "success")
        return redirect(url_for('index'))
    return render_template("form.html", action="Add", task=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    task = query_db("SELECT * FROM tasks WHERE id = ?", (id,), one=True)
    if not task:
        flash("Task not found", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        description = request.form.get('description','').strip()
        category = request.form.get('category','').strip()
        due_date = request.form.get('due_date','').strip()
        priority = request.form.get('priority','Normal')
        status = request.form.get('status','Pending')
        if not title:
            flash("Title is required", "warning")
            return redirect(url_for('edit', id=id))
        with sqlite3.connect(DB) as con:
            con.execute("""
                UPDATE tasks
                SET title=?, description=?, category=?, due_date=?, priority=?, status=?
                WHERE id=?
            """, (title, description, category or None, due_date or None, priority, status, id))
        flash("Task updated", "success")
        return redirect(url_for('index'))
    return render_template("edit.html", task=task)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM tasks WHERE id=?", (id,))
    flash("Task deleted", "info")
    return redirect(url_for('index'))

@app.route('/complete/<int:id>', methods=['POST'])
def complete(id):
    with sqlite3.connect(DB) as con:
        con.execute("UPDATE tasks SET status='Completed' WHERE id=?", (id,))
    flash("Task marked as completed", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
