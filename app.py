from flask import Flask, redirect, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date

# create instance
app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)


with app.app_context():
    db.create_all()


# home decorator
@app.route("/")
def index():
    return render_template("index.html")

# additional check
if __name__ == "__main__":
    app.run(debug=True, port=4848)