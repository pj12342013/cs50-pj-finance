import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    stocks = db.execute("SELECT company, SUM(quantity) AS quantities FROM buylist WHERE user_id = :u_id GROUP BY company HAVING SUM(quantity) > 0", u_id = session['user_id'])

    cash = db.execute("SELECT cash FROM users WHERE id = :u_id", u_id=session['user_id']  )

    quotes={}

    current_cash = round((cash[0]['cash']), 2)

    for stock in stocks:
        quotes[stock['company']] = lookup(stock['company'])

    return render_template("index.html", quotes=quotes, stocks=stocks, cash=current_cash)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    stocks = ['MSFT', 'AMZN', 'GOOG', 'AAPL', 'FB']

    stock_data={}

    for a in stocks:
        stock_data[a] = lookup(a)

    if request.method == "POST":

        sym = lookup(request.form.get("symbol"))

        if sym == None:
            flash("Enter Valid Symbol")
            return render_template("buy.html")

        else:
            user = db.execute("SELECT * FROM users WHERE id = :u_id", u_id = session['user_id'])
            funds = float(user[0]['cash'])

            no_of_shares = request.form.get("shares")

            total_price = float(no_of_shares) * float(sym['price'])

            if funds < total_price:
                flash("Not enough funds")
                return render_template("buy.html")
            elif funds >= total_price:
                funds -= total_price
                update_cash = db.execute("UPDATE users SET cash = :funds WHERE id = :u_id", funds = funds, u_id = session['user_id'])
                transaction = db.execute("INSERT INTO buylist(user_id, company, quantity, price, total, trans) VALUES(:u_id, :comp, :qty, :price, :total, 'BUY')", u_id=session['user_id'], comp=sym['symbol'], qty=no_of_shares, price=sym['price'], total=total_price)
                flash("Bought")
                return redirect("/")

    else:
        return render_template("buy.html", stock_data=stock_data)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    data = db.execute("SELECT company, quantity, price, total, transacted FROM buylist WHERE user_id = :u_id", u_id = session['user_id'])

    return render_template("history.html", data=data)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Show Account Details"""

    if request.method == "POST":

        return render_template("change.html")

    else:
        return render_template("account.html")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """change password"""

    if request.method == "POST":

        pass_hash = generate_password_hash(request.form.get("new password"))

        current_pass = db.execute("SELECT hash FROM users WHERE id = :u_id", u_id = session['user_id'])

        #if new password matches old password
        if check_password_hash(current_pass[0]['hash'], request.form.get("new password")):
            flash("New Password cannot be same as old password")
            return render_template("change.html")

        elif not check_password_hash(pass_hash, request.form.get("reconfirm password")):
            flash("Passwords do not match")
            return render_template("change.html")

        elif not request.form.get("new password")  or not request.form.get("reconfirm password"):
            flash("Password cannot be blank")
            return render_template("change.html")

        else:
            change_password = db.execute("UPDATE users SET hash=:passw WHERE id = :u_id", passw=pass_hash, u_id=session['user_id'])
            flash("password successfully changed")
            return redirect("/")

    else:
        return render_template("change.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must Provide Username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must Provide Password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid Username/Password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/stocks")
@login_required
def stocks():
    """""show top stocks """""

    stocks = ['MSFT', 'AMZN', 'GOOG', 'AAPL', 'FB', 'INTC', 'CSCO','CMCSA', 'PEP', 'ADBE', 'NVDA', 'NFLX', 'PYPL', 'COST', 'AMGN', 'AVGO', 'TXN']

    stock_data={}

    for a in stocks:
        stock_data[a] = lookup(a)
    return render_template("stocks.html", stock_data=stock_data)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method =="POST":

        sym = lookup(request.form.get("symbol"))

        #ensure symbol not empty form and valid
        if sym == None:
            flash("Enter Valid Symbol")
            return render_template("quote.html")


        else:
            return render_template("show_quote.html", sym=sym)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        #generate password hash
        pass_hash = generate_password_hash(request.form.get("password"))

        check_user = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        #ensure username submitted
        if not request.form.get("username"):
            flash("Must Provide Username")
            return render_template("register.html")
            #return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must Provide Password")
            return render_template("register.html")
            #return apology("must provide password", 403)

        #ensure passwords match
        elif request.form.get("password") != request.form.get("reconfirm password"):
            flash("passwords do not match")
            return render_template("register.html")
        #ensure unique username
        elif len(check_user) != 0:
            flash("Username already taken")
            return render_template("register.html")

        else:
            rows = db.execute("INSERT INTO users(username, hash, cash) VALUES(:username, :pass_hash, 10000)",
            username=request.form.get("username"), pass_hash=pass_hash)
            flash("Successly Registered, please log in")
            return render_template("login.html")
            # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")





@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    check_stock = db.execute("SELECT company FROM buylist WHERE user_id = :u_id GROUP BY company HAVING SUM(quantity) > 0", u_id = session['user_id'])


    """Sell shares of stock"""
    if request.method == "POST":

        #{'name': 'Apple, Inc.', 'price': 110.44, 'symbol': 'AAPL'}
        comp = lookup(request.form.get("symbol"))

        number = int(request.form.get("shares"))

        #check if they that many shares

        act_qty = db.execute("SELECT SUM(quantity) AS quantities FROM buylist WHERE user_id = :u_id AND company = :comp", u_id = session['user_id'], comp=comp['symbol'])

        amt =db.execute("SELECT cash FROM users WHERE id = :u_id", u_id=session['user_id'])

        balance = amt[0]['cash']

        act = act_qty[0]['quantities']

        if act < number:
            flash("Not enough shares")
            return render_template("sell.html", check_stock=check_stock)
        else:
            act -= number
            total= float(comp['price']) * number
            number = -(number)
            new_bal = balance + total

            db.execute("INSERT INTO buylist(user_id, company, quantity, price, total, trans) VALUES(:u_id, :comp, :qty, :price, :total , 'SELL')", u_id=session['user_id'], comp=comp['symbol'], qty=number, price=comp['price'], total=total)
            db.execute("UPDATE users SET cash = :cash WHERE id = :u_id", u_id = session['user_id'], cash = new_bal)
            flash("Sold")
            return redirect("/")
    else:
        return render_template("sell.html", check_stock=check_stock)


@app.route("/leaderboard")
@login_required
def leaderboard():

    ranks = db.execute("SELECT username, cash FROM users ORDER BY cash DESC LIMIT 10;")

    return render_template("leaderboard.html", ranks=ranks)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
