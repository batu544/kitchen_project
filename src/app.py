from flask import Flask, render_template
from menu import menu_bp
from order import order_bp
from payments import payment_bp

app = Flask(__name__)
app.register_blueprint(menu_bp)
app.register_blueprint(order_bp)
app.register_blueprint(payment_bp)

@app.route("/")
def home():
    return render_template("home.html")  # flask will find home.html in template folder


# @app.route("/orders")
# def orders():
#     return render_template("order_tracking.html")


@app.route("/inventory_management")
def inventory_management():
    return "inventory_management in progress"


@app.route("/reports")
def reports():
    return "Reports sections. Coming soon"


if __name__ == "__main__":
    app.run(debug=True)
    # print(app.url_map)
