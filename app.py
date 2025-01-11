from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    transactions = c.fetchall()

    c.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    total_expense = c.fetchone()[0] or 0
    current_balance = total_income - total_expense

    conn.close()
    return render_template('index.html', transactions=transactions, balance=current_balance, income=total_income, expense=total_expense)

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        transaction_type = request.form['type']
        category = request.form['category']
        amount = float(request.form['amount'])
        date = request.form['date']
        description = request.form['description']

        conn = sqlite3.connect('finances.db')
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (type, category, amount, date, description) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  (transaction_type, category, amount, date, description))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add.html')

@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()

    if request.method == 'POST':
        transaction_type = request.form['type']
        category = request.form['category']
        amount = float(request.form['amount'])
        date = request.form['date']
        description = request.form['description']

        c.execute('''UPDATE transactions 
                     SET type=?, category=?, amount=?, date=?, description=? 
                     WHERE id=?''', 
                  (transaction_type, category, amount, date, description, transaction_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    c.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
    transaction = c.fetchone()
    conn.close()
    return render_template('edit.html', transaction=transaction)

@app.route('/delete/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
    conn.commit()

    if c.rowcount > 0:
        conn.close()
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'success': False, 'error': 'Transaction not found'}), 404

@app.route('/transaction/<int:transaction_id>')
def get_transaction_details(transaction_id):
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
    transaction = c.fetchone()
    conn.close()

    if transaction:
        return jsonify({
            'id': transaction[0],
            'type': transaction[1],
            'category': transaction[2],
            'amount': transaction[3],
            'date': transaction[4],
            'description': transaction[5]
        })
    else:
        return jsonify({'error': 'Transaction not found'}), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
