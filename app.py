from flask import Flask, redirect, render_template, url_for, request, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import date, datetime

from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin # UserMixin give us objects like isactive user_id..
from sqlalchemy import text
import re
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import timedelta



# Database instance
db = SQLAlchemy()
login_manager = LoginManager()

# Application Factory
def create_app():
    app = Flask(__name__)

    # Database Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # fake db
    # app.config['SQLALCHEMY_BINDS'] = {
    #     'users': 'sqlite:///app.db'
    # }

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['REMEBER_COOKIE_DURATION'] = timedelta(days=15)
    app.config['SECRET_KEY'] = 'my-secret-key-for-cs50-final-exam'

    # Initialize database with app
    db.init_app(app)
    login_manager.init_app(app)
    # set the function that to be triggering and redirect to when protection
    # login_manager required to have a user Model
    login_manager.login_view = "login"


    @app.route("/health/db")
    def health_db():
        try:
            db.session.execute(text("SELECT 1"))
            return {"db": "ok"}, 200
        except Exception as e:
            return {"db", "error"}, 404


    # MODELS
    class Expense(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        description = db.Column(db.String(120), nullable=False)
        amount = db.Column(db.Float, nullable=False)
        category = db.Column(db.String(50), nullable=False)
        date = db.Column(db.Date, nullable=False, default=date.today)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    class user(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique = True, nullable=False)
        email = db.Column(db.String(120), unique = True, nullable=False)
        password_hash = db.Column(db.String(255), nullable=False)

        def __repr__(self):
            return f"<User {self.username}>"

    


    # Create database only when it doesn't exist
    with app.app_context():
        db.create_all()


    CATEGORIES = [
        'Food',
        'Transport',
        'Rent',
        'Utilities',
        'Health',
        'Invest'
    ]


    # Helper function
    def parse_date_or_none(s: str):
        if not s:
            return None

        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None

    # houme route
    @app.route("/")
    def index():
        return render_template("index.html")

    # dashboard route
    @app.route("/dashboard")
    @login_required
    def dashboard():

        start_str = (request.args.get("start") or "").strip()
        end_str = (request.args.get("end") or "").strip()
        selected_category = (request.args.get("category") or "").strip()

        start_date = parse_date_or_none(start_str)
        end_date = parse_date_or_none(end_str)

        if start_date and end_date and end_date < start_date:
            flash("Check your dates", "error")

            start_date = end_date = None
            start_str = end_str = ""

        q = Expense.query.filter_by(user_id=current_user.id)

        if start_date:
            q = q.filter(Expense.date >= start_date)

        if end_date:
            q = q.filter(Expense.date <= end_date)

        if selected_category:
            q = q.filter(Expense.category == selected_category)

        expenses = q.order_by(
            Expense.date.desc(),
            Expense.id.desc()
        ).all()

        total = round(sum(e.amount for e in expenses), 2)


        # Pie chart
        cat_q = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).filter(Expense.user_id==current_user.id)

        if start_date:
            cat_q = cat_q.filter(Expense.date >= start_date)

        if end_date:
            cat_q = cat_q.filter(Expense.date <= end_date)

        if selected_category:
            cat_q = cat_q.filter(
                Expense.category == selected_category
            )

        cat_rows = cat_q.group_by(Expense.category).all()

        cat_labels = [c for c, _ in cat_rows]
        cat_values = [
            round(float(s or 0), 2)
            for _, s in cat_rows
        ]


        # Day chart
        day_q = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).filter(Expense.user_id==current_user.id)

        if start_date:
            day_q = day_q.filter(Expense.date >= start_date)

        if end_date:
            day_q = day_q.filter(Expense.date <= end_date)

        if selected_category:
            day_q = day_q.filter(
                Expense.category == selected_category
            )

        day_rows = day_q.group_by(
            Expense.category
        ).order_by(Expense.date).all()

        day_labels = [d for d, _ in day_rows]
        day_values = [
            round(float(s or 0), 2)
            for _, s in day_rows
        ]


        return render_template(
            "dashboard.html",
            categories=CATEGORIES,
            today=date.today().isoformat(),
            expenses=expenses,
            total=total,
            start_str=start_str,
            end_str=end_str,
            selected_category=selected_category,
            cat_labels=cat_labels,
            cat_values=cat_values,
            day_labels=day_labels,
            day_values=day_values
        )


    @app.route('/register', methods=["GET", "POST"])
    def register():

        errors = []

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip()
            password = request.form.get("password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            # VALIDATION    
            required_fields = [username, email, password, confirm_password]

            if not all(required_fields):
                errors.append("fill in all the gaps")
                

            if not (3 <= len(username) <= 50):
                errors.append("username must be more than 3 characters")
                

            # check email pattern

            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                errors.append("invalid email!")

            if len(password) < 6:
                errors.append("password should be more than 6 characters")
            if password != confirm_password:
                errors.append("passwords don't match")

            # existing user
            existing_user = user.query.filter((user.username == username) | (user.email == email)).first()
            if existing_user:
                flash("you already registered", "error")
                errors.append("already registered!, login instead")
                return redirect(url_for("register"))  

            if not errors:
                try:
                    hashed_password = generate_password_hash(password) 


                    # create a new user
                    new_user = user(username=username, email=email, password_hash=hashed_password)
                    db.session.add(new_user)
                    db.session.commit()

                    # flash message
                    flash("Account created successfuly", "success")
                    return redirect(url_for("login"))

                except IntegrityError:
                    db.session.rollback()
                    errors.append("that username or email already registered!")

                    flash("Username or email already exists", "error")

        return render_template('register.html', errors=errors)

    
    
    @app.route('/login', methods=["GET", "POST"])
    def login():
        errors = []

        if request.method == "POST":
            email = (request.form.get("email") or "").strip()
            password = request.form.get("password") or ""

            if not email:
                errors.append("email is required!")
            if not password:
                errors.append("password is required!")

            if not errors:
                User = user.query.filter_by(email=email).first()

                if not User or not check_password_hash(User.password_hash, password):
                    errors.append("Invalid email or password")
                else:
                    remember_me = request.form.get("remember") == "1"

                    login_user(User, remember=remember_me)
                    flash(f"welcome back {User.username}", "success")


                    return redirect(url_for("dashboard"))




        return render_template('login.html', errors=errors)


    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("see you next time", "success")
        return redirect(url_for("index"))

    @app.route("/change_password", methods=["GET", "POST"])
    @login_required
    def change_password():
        
        errors = []

        if request.method == "POST":
                current_password = request.form.get("current_password") or ""
                new_password = request.form.get("new_password") or ""
                confirm_password = request.form.get("confirm_password") or ""

                if not check_password_hash(current_user.password_hash, current_password):
                    errors.append("current password is incorrect")
                if len(new_password) < 6:
                    errors.append("new password should be more than 6 characters")
                if new_password != confirm_password:
                    errors.append("new password and confirmation doesn't match!")
                if not errors:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()

                flash("Password updated successfuly!", "success")
                return redirect(url_for("dashboard"))

        return render_template("change_password.html", errors=errors)



    

    @login_manager.user_loader
    def load_user(user_id):
        return user.query.get(int(user_id))




    # Add expense
    @app.route("/add", methods=['POST'])
    @login_required
    def add():

        description = (
            request.form.get("description") or ""
        ).strip()

        amount_str = (
            request.form.get("amount") or ""
        ).strip()

        category = (
            request.form.get("category") or ""
        ).strip()

        date_str = (
            request.form.get("date") or ""
        ).strip()


        if not description or not amount_str or not category or not date_str:
            flash("Please fill all the fields", "error")
            return redirect(url_for("dashboard"))


        try:
            amount = float(amount_str)

            if amount <= 0:
                raise ValueError

        except ValueError:
            flash("Amount must be a positive number", "error")
            return redirect(url_for("dashboard"))


        try:
            d = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            d = date.today()


        e = Expense(
            description=description,
            amount=amount,
            category=category,
            date=d,
            user_id=current_user.id
        )

        db.session.add(e)
        db.session.commit()

        flash("Expense added!", "success")

        return redirect(url_for("dashboard"))


    # Delete expense
    @app.route("/delete/<int:expense_id>", methods=['POST'])
    @login_required
    def delete(expense_id):

        # e = Expense.query.get_or_404(expense_id)
        e = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

        db.session.delete(e)
        db.session.commit()

        flash("Expense deleted", "success")

        return redirect(url_for("dashboard"))


    # Edit expense - GET
    @app.route("/edit/<int:expense_id>", methods=['GET'])
    @login_required
    def edit(expense_id):

        e = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()


        return render_template(
            "edit.html",
            expense=e,
            categories=CATEGORIES,
            today=date.today().isoformat()
        )


    # Edit expense - POST
    @app.route("/edit/<int:expense_id>", methods=['POST'])
    def edit_post(expense_id):

        e = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()


        description = (
            request.form.get("description") or ""
        ).strip()

        amount_str = (
            request.form.get("amount") or ""
        ).strip()

        category = (
            request.form.get("category") or ""
        ).strip()

        date_str = (
            request.form.get("date") or ""
        ).strip()


        if not description or not amount_str or not category:
            flash("Please fill all the fields", "error")

            return redirect(
                url_for("edit", expense_id=expense_id)
            )


        try:
            amount = float(amount_str)

            if amount <= 0:
                raise ValueError

        except ValueError:
            flash("Amount must be a positive number", "error")

            return redirect(
                url_for("edit", expense_id=expense_id)
            )


        try:
            d = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash("Invalid date", "error")

            return redirect(
                url_for("edit", expense_id=expense_id)
            )


        e.description = description
        e.amount = amount
        e.category = category
        e.date = d

        db.session.commit()

        flash("Expense updated!", "success")

        return redirect(url_for("dashboard"))


    # Export CSV
    @app.route("/export.csv")
    @login_required
    def export_csv():

        start_str = (
            request.args.get("start") or ""
        ).strip()

        end_str = (
            request.args.get("end") or ""
        ).strip()

        selected_category = (
            request.args.get("category") or ""
        ).strip()


        start_date = parse_date_or_none(start_str)
        end_date = parse_date_or_none(end_str)


        q = Expense.query.filter_by(user_id=current_user.id)

        if start_date:
            q = q.filter(Expense.date >= start_date)

        if end_date:
            q = q.filter(Expense.date <= end_date)

        if selected_category:
            q = q.filter(
                Expense.category == selected_category
            )


        expenses = q.order_by(
            Expense.date,
            Expense.id
        ).all()


        lines = [
            "date, description, category, amount"
        ]

        for e in expenses:
            lines.append(
                f"{e.date.isoformat()}, "
                f"{e.description}, "
                f"{e.category}, "
                f"{e.amount:.2f}"
            )


        csv_data = "\n".join(lines)

        fname_start = start_str or "all"
        fname_end = end_str or "all"

        filename = (
            f"expenses_{fname_start}_to_{fname_end}.csv"
        )


        return Response(
            csv_data,
            headers={
                "Content-Type": "text/csv",
                "Content-Disposition":
                    f"attachment; filename={filename}"
            }
        )


    return app

# Run application
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=4848)