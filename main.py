# main.py (complete, clean version)
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import matplotlib.pyplot as plt
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_NAME = 'expenses.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            salary REAL DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            amount REAL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        salary = request.form.get('salary')

        if not username or not email or not password:
            error = "Please fill all required fields."
        else:
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO users (username, email, password, salary)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password, salary))
                conn.commit()

                user_id = c.lastrowid  # get newly created user ID
                session['user_id'] = user_id
                conn.close()

                return redirect(url_for('tracker'))

            except sqlite3.IntegrityError:
                error = "Username or email already exists."

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        identity = request.form.get('identity')
        password = request.form.get('password')

        if not identity or not password:
            error = "Please fill out both fields."
        else:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = ? OR email = ?", (identity, identity))
            user = c.fetchone()
            conn.close()

            if user is None:
                error = "Account not found. Please register first."
            elif user[1] != password:
                error = "Incorrect password."
            else:
                session['user_id'] = user[0]
                return redirect(url_for('tracker'))

    return render_template('login.html', error=error)

@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Handle expense form submission
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        description = request.form.get('description') or ""

        if category and amount:
            try:
                created_at = datetime.now().strftime('%Y-%m-%d')
                c.execute('''
                    INSERT INTO expenses (user_id, category, amount, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, category, amount, description, created_at))
                conn.commit()
            except Exception as e:
                print(f"[ERROR] Failed to insert expense: {e}")

    # Get salary
    c.execute("SELECT salary FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    salary = row[0] if row else 0

    # Get total spent and expenses this month
    now = datetime.now()
    current_month = now.strftime('%Y-%m')

    c.execute("""
        SELECT created_at, category, amount, description
        FROM expenses
        WHERE user_id = ?
          AND substr(created_at, 1, 7) = ?
        ORDER BY created_at DESC
    """, (user_id, current_month))
    expenses = c.fetchall()

    c.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id = ?
          AND substr(created_at, 1, 7) = ?
    """, (user_id, current_month))
    total_spent = c.fetchone()[0] or 0

    remaining_balance = salary - total_spent
    average_spent = total_spent
    conn.close()

    # Create chart
    static_folder = os.path.join(app.root_path, 'static')
    os.makedirs(static_folder, exist_ok=True)

    labels = ['Spent', 'Remaining']
    sizes = [total_spent, remaining_balance]
    colors = ['#ff9999', '#66b3ff']
    explode = (0.1, 0)

    fig, ax = plt.subplots()
    ax.pie(sizes, explode=explode, labels=labels, colors=colors,
           autopct='%1.1f%%', shadow=True, startangle=90)
    ax.axis('equal')

    chart_filename = f'pie_{user_id}.png'
    chart_path = os.path.join(static_folder, chart_filename)
    plt.savefig(chart_path)
    plt.close()

    current_month_name = now.strftime('%B %Y')

    return render_template('tracker.html',
                           salary=salary,
                           total_spent=total_spent,
                           remaining=remaining_balance,
                           average_spent=average_spent,
                           chart_url=chart_filename,
                           expenses=expenses,
                           current_month=current_month_name)

@app.route('/delete_expenses', methods=['POST'])
def delete_expenses():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect('/tracker')

@app.route('/start_new_month', methods=['POST'])
def start_new_month():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect('/tracker')

if __name__ == '__main__':
    #init_db()  # ✅ important
    app.run(debug=True)
