from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, flash

app = Flask(__name__)

app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(200))

# Database Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)


# Create database
with app.app_context():
    db.create_all()


# Home Route
@app.route('/')
def index():

    if 'user_id' not in session:
        return redirect('/login')

    expenses = Expense.query.all()

    total = sum(exp.amount for exp in expenses)

    category_totals = {}

    for exp in expenses:
        if exp.category in category_totals:
            category_totals[exp.category] += exp.amount
        else:
            category_totals[exp.category] = exp.amount

    current_month = datetime.utcnow().month

    monthly_total = sum(
        exp.amount for exp in expenses
        if exp.date.month == current_month
    )

    return render_template(
        'index.html',
        expenses=expenses,
        total=total,
        monthly_total=monthly_total,
        categories=list(category_totals.keys()),
        amounts=list(category_totals.values())
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

        if check_password_hash(user.password,password):

            session['user_id'] = user.id
            return redirect('/')

        else:
            flash("Incorrect password")

    return render_template("login.html")

@app.route('/logout')
def logout():

    session.pop('user_id', None)

    return redirect('/login')

# Add Expense
@app.route('/add', methods=['POST'])
def add_expense():

    amount = float(request.form['amount'])
    category = request.form['category']
    description = request.form['description']

    if category == "Other":
        category = request.form['otherCategory']

    new_expense = Expense(
        amount=amount,
        category=category,
        description=description
    )

    db.session.add(new_expense)
    db.session.commit()

    return redirect('/')


# Delete Expense
@app.route('/delete/<int:id>')
def delete(id):

    expense = Expense.query.get(id)

    db.session.delete(expense)
    db.session.commit()

    return redirect('/')


# Edit Expense
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):

    expense = Expense.query.get(id)

    if request.method == 'POST':

        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.description = request.form['description']

        db.session.commit()

        return redirect('/')

    return render_template('edit.html', expense=expense)


if __name__ == "__main__":
    app.run(debug=True)