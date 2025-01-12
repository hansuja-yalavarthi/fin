from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, Response, send_file
from datetime import datetime
import sqlite3
import csv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()

    # Transactions table
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

    # Budget table
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            budget_limit REAL NOT NULL
        )
    ''')

    # Savings Goals table
    c.execute('''
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_savings REAL NOT NULL,
            due_date TEXT
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

@app.route('/edit_transaction', methods=['POST'])
def edit_transaction():
    # Get form data
    transaction_id = request.form['transaction_id']
    transaction_type = request.form['type']
    category = request.form['category']
    amount = request.form['amount']
    date = request.form['date']
    description = request.form['description']

    # Connect to the database and update the transaction
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()

    # Update the transaction in the database
    c.execute('''UPDATE transactions
                 SET type = ?, category = ?, amount = ?, date = ?, description = ?
                 WHERE id = ?''', 
              (transaction_type, category, amount, date, description, transaction_id))
    
    conn.commit()

    # Check if the update was successful
    if c.rowcount > 0:
        conn.close()
        return jsonify({'success': True})
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Transaction not found'})

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

@app.route('/export/csv')
def export_csv():
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    transactions = c.fetchall()
    conn.close()

    csv_data = [['ID', 'Type', 'Category', 'Amount', 'Date', 'Description']]  # CSV header
    csv_data += [[t[0], t[1], t[2], t[3], t[4], t[5]] for t in transactions]

    def generate():
        for row in csv_data:
            yield ','.join(map(str, row)) + '\n'

    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment;filename=transactions.csv'
    })


@app.route('/export/pdf')
def export_pdf():
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    transactions = c.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Transactions Report")
    c.drawString(50, 730, "ID    Type    Category    Amount    Date    Description")

    y = 710
    for t in transactions:
        c.drawString(50, y, f"{t[0]}  {t[1]}  {t[2]}  ${t[3]}  {t[4]}  {t[5]}")
        y -= 20
        if y < 50:  # New page if content exceeds
            c.showPage()
            y = 750

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="transactions.pdf", mimetype='application/pdf')

@app.route('/budgeting', methods=['GET', 'POST'])
def budgeting():
    if request.method == 'POST':
        # Handle budget category updates
        category = request.form['category']
        budget_limit = float(request.form['budget_limit'])

        conn = sqlite3.connect('finances.db')
        c = conn.cursor()
        c.execute('''INSERT INTO budgets (category, budget_limit) VALUES (?, ?)''', 
                  (category, budget_limit))
        conn.commit()
        conn.close()

        return redirect(url_for('budgeting'))

    # Retrieve current budgets
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM budgets")
    budgets = c.fetchall()
    conn.close()

    return render_template('budgeting.html', budgets=budgets)


@app.route('/savings', methods=['GET', 'POST'])
def savings():
    if request.method == 'POST':
        # Handle savings goal updates
        goal_name = request.form['goal_name']
        target_amount = float(request.form['target_amount'])
        current_savings = float(request.form['current_savings'])
        due_date = request.form['due_date']

        conn = sqlite3.connect('finances.db')
        c = conn.cursor()
        c.execute('''INSERT INTO savings_goals (goal_name, target_amount, current_savings, due_date)
                     VALUES (?, ?, ?, ?)''', 
                  (goal_name, target_amount, current_savings, due_date))
        conn.commit()
        conn.close()

        return redirect(url_for('savings'))

    # Retrieve current savings goals
    conn = sqlite3.connect('finances.db')
    c = conn.cursor()
    c.execute("SELECT * FROM savings_goals")
    goals = c.fetchall()
    conn.close()

    return render_template('savings.html', goals=goals)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
