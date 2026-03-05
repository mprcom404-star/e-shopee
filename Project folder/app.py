from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
import razorpay
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------------
# FILE UPLOAD
# -------------------------

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------------
# DATABASE
# -------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///marketplace.db"
db = SQLAlchemy(app)

# -------------------------
# GOOGLE LOGIN
# -------------------------

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_SECRET",
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'}
)

# -------------------------
# RAZORPAY
# -------------------------

RAZORPAY_KEY_ID = "YOUR_RAZORPAY_KEY"
RAZORPAY_SECRET = "YOUR_RAZORPAY_SECRET"

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET)
)

# -------------------------
# DATABASE MODELS
# -------------------------

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    email = db.Column(db.String(120), unique=True)

    password = db.Column(db.String(100))

    verified = db.Column(db.Boolean, default=False)

    is_admin = db.Column(db.Boolean, default=False)


class Product(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200))

    price = db.Column(db.Integer)

    category = db.Column(db.String(100))

    description = db.Column(db.Text)

    image = db.Column(db.String(200))

    seller = db.Column(db.Integer)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)

class Wishlist(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    product_id = db.Column(db.Integer)


class Rating(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    rating = db.Column(db.Integer)

    product_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer)


class Notification(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    message = db.Column(db.String(200))

    user_id = db.Column(db.Integer)


class Order(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer)

    buyer_id = db.Column(db.Integer)

    seller_id = db.Column(db.Integer)

    price = db.Column(db.Integer)

    # Added fields
    name = db.Column(db.String(200))

    email = db.Column(db.String(200))

    phone = db.Column(db.String(20))

    address = db.Column(db.Text)

    payment_id = db.Column(db.String(200))

    status = db.Column(db.String(50), default="Processing")

    date = db.Column(db.DateTime, default=db.func.current_timestamp())


with app.app_context():
    db.create_all()
#DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    wishlist_items = Wishlist.query.filter_by(
        user_id=session["user_id"]
    ).all()

    products = []

    for w in wishlist_items:
        product = Product.query.get(w.product_id)
        if product:
            products.append(product)

    return render_template(
        "dashboard.html",
        wishlist=products
    )

# -------------------------
# HOME + SEARCH + FILTER
# -------------------------

@app.route("/")
def home():

    search = request.args.get("search")

    category = request.args.get("category")

    sort = request.args.get("sort")

    query = Product.query

    if search:
        query = query.filter(Product.name.contains(search))

    if category:
        query = query.filter(Product.category == category)

    if sort == "low":
        query = query.order_by(Product.price.asc())

    if sort == "high":
        query = query.order_by(Product.price.desc())

    items = query.all()

    return render_template("index.html", items=items)

# -------------------------
# REGISTER
# -------------------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        password = request.form["password"]

        verified = email.endswith(".edu")

        user = User(
            name=name,
            email=email,
            password=password,
            verified=verified
        )

        db.session.add(user)

        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user_id"] = user.id
            session["user"] = user.name
            return redirect("/")

        else:
            return "Invalid Email or Password"

    return render_template("login.html")

# -------------------------
# GOOGLE LOGIN
# -------------------------

@app.route("/google-login")
def google_login():

    redirect_uri = url_for("google_auth", _external=True)

    return google.authorize_redirect(redirect_uri)


@app.route("/google-auth")
def google_auth():

    token = google.authorize_access_token()

    resp = google.get('userinfo')

    user_info = resp.json()

    email = user_info["email"]

    name = user_info["name"]

    user = User.query.filter_by(email=email).first()

    if not user:

        user = User(name=name,email=email,verified=True)

        db.session.add(user)

        db.session.commit()

    session["user_id"] = user.id

    session["user"] = user.name

    return redirect("/")

# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.context_processor
def inject_user():

    if "user_id" in session:
        user = User.query.get(session["user_id"])
        return dict(current_user=user)

    return dict(current_user=None)
#delete
@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user.is_admin:
        return "Access Denied"

    users = User.query.all()
    products = Product.query.all()
    orders = Order.query.all()

    total_sales = sum(order.price for order in orders)

    return render_template(
        "admin.html",
        users=users,
        products=products,
        orders=orders,
        total_sales=total_sales
    )
@app.route("/delete-product/<int:id>")
def delete_product(id):

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])
    if not user.is_admin:
        return "Access Denied"

    product = Product.query.get(id)

    db.session.delete(product)
    db.session.commit()

    return redirect("/admin")

# -------------------------
# PROFILE TAB
# -------------------------

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    orders = Order.query.filter_by(buyer_id=user.id).all()

    return render_template(
        "profile.html",
        user=user,
        orders=orders
    )

# -------------------------
# EDIT PROFILE
# -------------------------

@app.route("/edit-profile", methods=["GET","POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if request.method == "POST":

        user.name = request.form["name"]

        user.email = request.form["email"]

        db.session.commit()

        return redirect("/profile")

    return render_template("edit_profile.html", user=user)

# -------------------------
# HELP CENTRE
# -------------------------

@app.route("/help")
def help_center():

    return render_template("help.html")

# -------------------------
# PRODUCT PAGE
# -------------------------

@app.route("/product/<int:id>")
def product(id):

    item = Product.query.get_or_404(id)

    ratings = Rating.query.filter_by(product_id=id).all()

    avg = 0

    if ratings:
        avg = sum([r.rating for r in ratings]) / len(ratings)

    return render_template("product.html", item=item, avg=avg)

# -------------------------
# ADD TO CART
# -------------------------

@app.route("/add-cart/<int:product_id>")
def add_cart(product_id):

    if "user_id" not in session:
        return redirect("/login")

    item = Cart.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if item:
        item.quantity += 1
    else:
        item = Cart(
            user_id=session["user_id"],
            product_id=product_id
        )
        db.session.add(item)

    db.session.commit()

    return redirect("/cart")
# -------------------------
# CART
# -------------------------

@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect("/login")

    cart_items = Cart.query.filter_by(user_id=session["user_id"]).all()

    products = []

    for c in cart_items:
        product = Product.query.get(c.product_id)
        if product:
            products.append(product)

    return render_template("cart.html", products=products)
#cart model
@app.context_processor
def inject_cart_count():
    if "user_id" in session:
        count = Cart.query.filter_by(user_id=session["user_id"]).count()
    else:
        count = 0
    return dict(cart_count=count)
# -------------------------
# CHECKOUT
# -------------------------

@app.route("/checkout/<int:product_id>", methods=["GET","POST"])
def checkout(product_id):

    if "user_id" not in session:
        return redirect("/login")

    product = Product.query.get(product_id)

    total = product.price

    if request.method == "POST":

        session["checkout"] = {
            "product_id": product.id,
            "name": request.form["name"],
            "email": request.form["email"],
            "phone": request.form["phone"],
            "address": request.form["address"]
        }

        return redirect("/pay")

    return render_template("checkout.html", product=product, total=total)
#pay
@app.route("/pay")
def pay():

    data = session.get("checkout")

    product = Product.query.get(data["product_id"])

    amount = int(product.price) * 100

    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return render_template(
        "payment.html",
        product=product,
        order_id=order["id"],
        amount=amount,
        key_id=RAZORPAY_KEY_ID
    )
# -------------------------
# PAYMENT SUCCESS
# -------------------------

@app.route("/payment-success", methods=["POST"])
def payment_success():

    payment_id = request.form["razorpay_payment_id"]

    cart_items = Cart.query.filter_by(user_id=session["user_id"]).all()

    shipping = session.get("checkout")

    for item in cart_items:

        product = Product.query.get(item.product_id)

        order = Order(
            product_id=product.id,
            buyer_id=session["user_id"],
            seller_id=product.seller,
            price=product.price,
            name=shipping["name"],
            email=shipping["email"],
            phone=shipping["phone"],
            address=shipping["address"],
            payment_id=payment_id,
            status="Paid"
        )

        db.session.add(order)

    Cart.query.filter_by(user_id=session["user_id"]).delete()

    db.session.commit()

    return redirect("/purchase-history")

# -------------------------
# SELL PRODUCT
# -------------------------

@app.route("/sell", methods=["GET","POST"])
def sell():

    if request.method == "POST":

        name = request.form["name"]

        price = int(request.form["price"])

        category = request.form["category"]

        description = request.form["description"]

        image = request.files["image"]

        filename = image.filename

        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        product = Product(
            name=name,
            price=price,
            category=category,
            description=description,
            image=filename,
            seller=session["user_id"]
        )

        db.session.add(product)

        db.session.commit()

        return redirect("/")

    return render_template("sell.html")
#whislist page
@app.route("/wishlist/<int:product_id>")
def add_wishlist(product_id):

    if "user_id" not in session:
        return redirect("/login")

    # check if already in wishlist
    existing = Wishlist.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if not existing:
        item = Wishlist(
            user_id=session["user_id"],
            product_id=product_id
        )
        db.session.add(item)
        db.session.commit()

    return redirect("/dashboard")
#Notifications page
@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect("/login")

    notes = Notification.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template("notification.html", notes=notes)
# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":
    app.run(debug=True)