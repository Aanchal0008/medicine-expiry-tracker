from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=720) 

# Initialize DB
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create medicines table
    c.execute('''CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        batch_number TEXT,
        expiry_date TEXT,
        quantity INTEGER,
        price REAL,
        alert_level INTEGER
    )''')

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    # Add default user if none exists
    c.execute("SELECT * FROM users")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()


@app.route('/')
def index():
    if 'user' not in session:
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))
    
    query = request.args.get('q', '').strip()

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if query:
        c.execute("SELECT * FROM medicines WHERE name LIKE ?", ('%' + query + '%',))
    else:
        c.execute("SELECT * FROM medicines")
    
    medicines = c.fetchall()
    c.execute("SELECT COUNT(*) FROM medicines")
    total_medicines = c.fetchone()[0]

    conn.close()

    today = datetime.today().date()
    soon = today + timedelta(days=30)

    expired = []
    near_expiry = []
    low_stock = []

    for med in medicines:
        exp_date = datetime.strptime(med[3], '%Y-%m-%d').date()
        if exp_date < today:
            expired.append(med)
        elif today <= exp_date <= soon:
            near_expiry.append(med)
        if med[4] <= med[6]:  # quantity <= alert_level
            low_stock.append(med)

    return render_template('index.html',
                       medicines=medicines,
                       expired=expired,
                       near_expiry=near_expiry,
                       low_stock=low_stock,
                       total_medicines=total_medicines)


@app.route('/add', methods=['GET', 'POST'])
def add_medicine():
    if request.method == 'POST':
        name = request.form['name']
        batch_number = request.form['batch_number']
        expiry_date = request.form['expiry_date']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        alert_level = int(request.form['alert_level'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO medicines (name, batch_number, expiry_date, quantity, price, alert_level) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, batch_number, expiry_date, quantity, price, alert_level))
        conn.commit()
        conn.close()
        flash('Medicine added successfully!')
        return redirect(url_for('index'))
    return render_template('add_medicine.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_medicine(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        # update
        name = request.form['name']
        batch = request.form['batch_number']
        expiry = request.form['expiry_date']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        alert = int(request.form['alert_level'])

        c.execute("""UPDATE medicines SET 
                    name=?, batch_number=?, expiry_date=?, quantity=?, price=?, alert_level=? 
                    WHERE id=?""",
                  (name, batch, expiry, quantity, price, alert, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # fetch for editing
    c.execute("SELECT * FROM medicines WHERE id=?", (id,))
    medicine = c.fetchone()
    conn.close()
    return render_template('edit_medicine.html', medicine=medicine)


@app.route('/delete/<int:id>')
def delete_medicine(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM medicines WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            session.permanent = True
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/expired')
def expired_medicines():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

    today = datetime.today().date()
    expired = [med for med in medicines if datetime.strptime(med[3], '%Y-%m-%d').date() < today]

    return render_template('expired.html', expired=expired)


@app.route('/near_expiry')
def near_expiry_medicines():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

    today = datetime.today().date()
    soon = today + timedelta(days=30)
    near_expiry = [med for med in medicines if today <= datetime.strptime(med[3], '%Y-%m-%d').date() <= soon]

    return render_template('near_expiry.html', near_expiry=near_expiry)


@app.route('/low_stock')
def low_stock_medicines():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

    low_stock = [med for med in medicines if med[4] <= med[6]]  # quantity <= alert_level

    return render_template('low_stock.html', low_stock=low_stock)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM medicines")
    medicines = c.fetchall()
    conn.close()

    today = datetime.today().date()
    soon = today + timedelta(days=30)

    total_medicines = len(medicines)
    expired = [med for med in medicines if datetime.strptime(med[3], '%Y-%m-%d').date() < today]
    near_expiry = [med for med in medicines if today <= datetime.strptime(med[3], '%Y-%m-%d').date() <= soon]
    low_stock = [med for med in medicines if med[4] <= med[6]]  # quantity <= alert_level

    return render_template('dashboard.html',
                           total_medicines=total_medicines,
                           expired=expired,
                           near_expiry=near_expiry,
                           low_stock=low_stock)



if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


def init_users_table():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')
    c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ('admin', 'admin'))
    conn.commit()
    conn.close()

init_users_table()

