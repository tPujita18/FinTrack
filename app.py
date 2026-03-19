from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, flash
from flask import jsonify
import csv
from flask import Response

app = Flask(__name__)

app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(200))

    last_login = db.Column(db.DateTime)   # NEW

# Database Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=False) 

# Create database
with app.app_context():
    db.create_all()


# Home Route
@app.route('/')
def index():

    if 'user_id' not in session:
        return redirect('/login')

    # ✅ DEFINE FIRST
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    # ✅ THEN USE
    total = sum(exp.amount for exp in expenses)

    category_totals = {}
    for exp in expenses:
        category_totals[exp.category] = category_totals.get(exp.category, 0) + exp.amount

    now = datetime.utcnow()

    monthly_total = sum(exp.amount for exp in expenses if exp.date.month == now.month)
    yearly_total = sum(exp.amount for exp in expenses if exp.date.year == now.year)

    user = User.query.get(session['user_id'])

    return render_template(
        'index.html',
        expenses=expenses,
        total=total,
        monthly_total=monthly_total,
        yearly_total=yearly_total,
        categories=list(category_totals.keys()),
        amounts=list(category_totals.values()),
        username=session.get('username'),
        last_login=user.last_login if user else None
    )

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        new_user = User(username=username, password=password)

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("User not registered. Register now.")
            return render_template("login.html")

        from datetime import datetime

        if check_password_hash(user.password, password):

            session['user_id'] = user.id
            session['username'] = user.username

            user.last_login = datetime.utcnow()   # NEW
            db.session.commit()

            return redirect('/')

        else:
            flash("Incorrect password")

    return render_template("login.html")

@app.route('/logout')
def logout():

    session.pop('user_id', None)

    return redirect('/login')

@app.route('/api/expenses')
def api_get_expenses():

    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    data = []

    for exp in expenses:
        data.append({
            "id": exp.id,
            "amount": exp.amount,
            "category": exp.category,
            "description": exp.description,
            "date": exp.date.strftime("%Y-%m-%d")
        })

    return jsonify(data)

@app.route('/api/expenses', methods=['POST'])
def api_add_expense():

    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    new_expense = Expense(
        amount=data['amount'],
        category=data['category'],
        description=data.get('description', ''),
        user_id=session['user_id']
    )

    db.session.add(new_expense)
    db.session.commit()

    return jsonify({"message": "Expense added"})

@app.route('/export')
def export_csv():

    if 'user_id' not in session:
        return redirect('/login')

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    def generate():
        data = [["Amount", "Category", "Description", "Date"]]

        for exp in expenses:
            data.append([
                exp.amount,
                exp.category,
                exp.description,
                exp.date.strftime("%Y-%m-%d")
            ])

        for row in data:
            yield ",".join(map(str, row)) + "\n"

    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=expenses.csv"}
    )

# Add Expense

@app.route('/add', methods=['POST'])
def add_expense():

    if 'user_id' not in session:
        return redirect('/login')

    amount = float(request.form['amount'])
    category = request.form['category']
    description = request.form['description']
    date_str = request.form['date']

    if category == "Other":
        category = request.form['otherCategory']

    # Convert string → datetime
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    new_expense = Expense(
        amount=amount,
        category=category,
        description=description,
        date=date_obj,
        user_id=session['user_id']
    )

    db.session.add(new_expense)
    db.session.commit()

    return redirect('/')

# Delete Expense
@app.route('/delete/<int:id>')
def delete(id):

    expense = Expense.query.filter_by(
        id=id,
        user_id=session['user_id']
    ).first()

    if expense:
        db.session.delete(expense)
        db.session.commit()

    return redirect('/')


# Edit Expense
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):

    expense = Expense.query.filter_by(
        id=id,
        user_id=session['user_id']
    ).first()

    if not expense:
        return redirect('/')

    if request.method == 'POST':

        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.description = request.form['description']

        db.session.commit()

        return redirect('/')

    return render_template('edit.html', expense=expense)

if __name__ == "__main__":
    app.run(debug=True)