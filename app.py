from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "ExCalSecretKey123"


# ==========================
# DATABASE CONNECTION
# ==========================

def get_db():
    return sqlite3.connect("ExCal.db")


# ==========================
# HOME
# ==========================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# REGISTER
# ==========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match!"

        conn = get_db()
        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users(fullname,email,password)
                VALUES(?,?,?)
            """, (fullname, email, password))

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()
            return "Email already exists!"

        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================
# LOGIN
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email=? AND password=?
        """, (email, password))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]

            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")


# ==========================
# DASHBOARD
# ==========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("ExCal.db")
    cursor = conn.cursor()

    # =========================
    # TOTAL INCOME
    # =========================

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM income
        WHERE user_id=?
    """, (session["user_id"],))

    total_income = cursor.fetchone()[0]

    # =========================
    # TOTAL EXPENSE
    # =========================

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
        WHERE user_id=?
    """, (session["user_id"],))

    total_expense = cursor.fetchone()[0]

    # =========================
    # BALANCE
    # =========================

    total_balance = total_income - total_expense

    # =========================
    # LATEST INCOME
    # =========================

    cursor.execute("""
        SELECT income_date,
               source,
               amount
        FROM income
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 5
    """, (session["user_id"],))

    incomes = cursor.fetchall()

    # =========================
    # LATEST EXPENSES
    # =========================

    cursor.execute("""
        SELECT expense_date,
               category,
               amount
        FROM expenses
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 5
    """, (session["user_id"],))

    expenses = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["user_name"],
        total_income=total_income,
        total_expense=total_expense,
        total_balance=total_balance,
        incomes=incomes,
        expenses=expenses
    )

# ==========================
# ADD INCOME
# ==========================

@app.route("/add-income", methods=["GET", "POST"])
def add_income():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        source = request.form["source"]
        amount = request.form["amount"]
        income_date = request.form["income_date"]
        notes = request.form["notes"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO income(
                user_id,
                source,
                amount,
                income_date,
                notes
            )
            VALUES(?,?,?,?,?)
        """, (
            session["user_id"],
            source,
            amount,
            income_date,
            notes
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_income.html")


# ==========================
# ADD EXPENSE
# ==========================

@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        amount = request.form["amount"]
        expense_date = request.form["expense_date"]
        notes = request.form["notes"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO expenses(
                user_id,
                title,
                category,
                amount,
                expense_date,
                notes
            )
            VALUES(?,?,?,?,?,?)
        """, (
            session["user_id"],
            title,
            category,
            amount,
            expense_date,
            notes
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_expense.html")



# ==========================
# REPORTS
# ==========================

@app.route("/reports")
def reports():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    user_id = session["user_id"]

    # ==========================
    # CURRENT MONTH
    # ==========================

    current_month = "strftime('%Y-%m','now')"

    # --------------------------
    # This Month Income
    # --------------------------

    cursor.execute(f"""
        SELECT IFNULL(SUM(amount),0)
        FROM income
        WHERE user_id=?
        AND substr(income_date,1,7)={current_month}
    """,(user_id,))

    month_income = cursor.fetchone()[0]

    # --------------------------
    # This Month Expense
    # --------------------------

    cursor.execute(f"""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
        WHERE user_id=?
        AND substr(expense_date,1,7)={current_month}
    """,(user_id,))

    month_expense = cursor.fetchone()[0]

    month_balance = month_income - month_expense

    # ==========================
    # TOTALS
    # ==========================

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM income
        WHERE user_id=?
    """,(user_id,))

    total_income = cursor.fetchone()[0]

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
        WHERE user_id=?
    """,(user_id,))

    total_expense = cursor.fetchone()[0]

    total_balance = total_income-total_expense

    # ==========================
    # CATEGORY PIE CHART
    # ==========================

    cursor.execute(f"""
        SELECT
            category,
            SUM(amount)
        FROM expenses
        WHERE user_id=?
        AND substr(expense_date,1,7)={current_month}
        GROUP BY category
    """,(user_id,))

    rows = cursor.fetchall()

    category_labels = []
    category_amounts = []

    for row in rows:

        category_labels.append(row[0])
        category_amounts.append(float(row[1]))

        # Category summary for reports.html
    category_summary = list(zip(category_labels, category_amounts))

    # ==========================
    # DAILY EXPENSE LINE CHART
    # ==========================

    cursor.execute(f"""
        SELECT
            substr(expense_date,9,2),
            SUM(amount)
        FROM expenses
        WHERE user_id=?
        AND substr(expense_date,1,7)={current_month}
        GROUP BY substr(expense_date,9,2)
        ORDER BY substr(expense_date,9,2)
    """,(user_id,))

    daily = cursor.fetchall()

    daily_labels=[]
    daily_amounts=[]

    for row in daily:

        daily_labels.append(row[0])
        daily_amounts.append(float(row[1]))

    # ==========================
    # LAST 10 TRANSACTIONS
    # ==========================

    cursor.execute("""

    SELECT
        income_date,
        source,
        amount,
        'Income'

    FROM income

    WHERE user_id=?

    UNION ALL

    SELECT
        expense_date,
        category,
        amount,
        'Expense'

    FROM expenses

    WHERE user_id=?

    ORDER BY 1 DESC

    LIMIT 10

    """,(user_id,user_id))

    transactions=cursor.fetchall()

    conn.close()

    return render_template(

    "reports.html",

    username=session["user_name"],

    total_income=total_income,
    total_expense=total_expense,
    total_balance=total_balance,

    month_income=month_income,
    month_expense=month_expense,
    month_balance=month_balance,

    category_labels=category_labels,
    category_amounts=category_amounts,
    category_summary=category_summary,

    daily_labels=daily_labels,
    daily_amounts=daily_amounts,

    transactions=transactions

)

# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================
# RUN
# ==========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

