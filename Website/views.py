from flask import Blueprint, render_template, request,jsonify, redirect, url_for

views = Blueprint(__name__, "views")

@views.route("/map/")
def map():
    return render_template("map.html")

@views.route("/")
def home():
    return render_template("index.html", name = "Data Structures")

@views.route("/test")
def test():
    return render_template("profile.html")


#Paramter so the website/user/<variable>
@views.route("/user/<username>")
def user(username):
    return render_template("index.html", name = username)

#Query paramater so the website/profile?name=
@views.route("/profile/")
def profile():
    args = request.args
    name = args.get('name')
    return render_template("index.html", name = name)

@views.route("/json")
def get_json():
    return jsonify({'name':'example', 'see':'5'})

@views.route("/data")
def get_data():
    data = request.json
    return jsonify(data)

@views.route("/go-to-home")
def go_to_home():
    return redirect(url_for("views.home"))