from flask import Flask, redirect, render_template, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

# create instance
app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['SECRET_KEY'] = 'my-secret-key'
db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)


# create db only when it doesn't exist
with app.app_context():
    db.create_all()


# home decorator
@app.route("/")
def index():
    expenses = Expense.query.order_by(Expense.date.desc(), Expense.id.desc()).all()
    return render_template("index.html", expenses=expenses)


# add decorator
@app.route("/add", methods=['POST'])
def add():
    description = (request.form.get("description") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    date_str = (request.form.get("date") or "").strip()

    if not description or not amount_str or not category or not date_str:
        flash("Please fill all the fields", "error")
        return redirect(url_for("index"))

    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number", "error")
        return redirect(url_for("index"))

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        d = date.today()

    e = Expense(description=description, amount=amount_str, category=category, date=d)
    db.session.add(e)
    db.session.commit()

    flash("Expense added!", "success")
    return redirect(url_for("index"))
    



# additional check
if __name__ == "__main__":
    app.run(debug=True, port=4848)