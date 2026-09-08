from flask import Flask, redirect, render_template, url_for

# create instance
app = Flask(__name__)

# home decorator
@app.route("/")
def index():
    return render_template("index.html")

# additional check
if __name__ == "__main__":
    app.run(debug=True, port=4848)