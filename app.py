from flask import Flask, render_template, redirect, url_for, request, session, flash, get_flashed_messages
from datetime import timedelta
from flask.templating import render_template_string
from flask_sqlalchemy import SQLAlchemy

import pandas as pd
import numpy as np
import os

from recommendation_model import Recommendation_Algorithm

# STARTING FLASK APP
app = Flask(__name__)
app.secret_key = "sdovibaeoub34008234bb2i3i"
app.permanent_session_lifetime = timedelta(days=7)

# CONFIGURING DATA BASE
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite3"
# app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["POSTGRESQL"]
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://guilevieiram:Aquario0.@database-1.cvjpiq5m2lty.eu-west-2.rds.amazonaws.com:5432/mydb"
# app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://klqyvsofizsjcb:b6ef78f91f8e3be4f5861c490efe52d99d6c1c1cb3c472839a90bf73db9704a7@ec2-54-157-100-65.compute-1.amazonaws.com:5432/d8pld4q9k569uv"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# TABLES CLASSES
class Users_Classifications(db.Model):
	__tablename__ = 'user_classifications'
	_id = db.Column("id", db.Integer, primary_key=True)
	user = db.Column("user", db.Text)
	recipe_id = db.Column("recipe_id", db.Integer)
	classification = db.Column("classification", db.Integer)

	def __init__(self, user, recipe_id, classification):
		self.user = user
		self.recipe_id = recipe_id
		self.classification = classification

class Recipes(db.Model):
	__tablename__='recipes'
	_id = db.Column("id", db.Integer, primary_key=True)
	title = db.Column(db.Text)
	description = db.Column(db.Text)
	recipe_link = db.Column(db.Text) 
	image_link = db.Column(db.Text)
	keywords = db.Column(db.Text)
	rating = db.Column(db.Float)
	rating_count = db.Column(db.Integer)
	category = db.Column(db.Text)
	cuisine = db.Column(db.Text)
	soup = db.Column(db.Text)

	def __init__(self, title, description, recipe_link, image_link, keywords, rating, rating_count, category, cuisine, soup):
		self.title = title
		self.description = description
		self.recipe_link = recipe_link
		self.image_link = image_link
		self.keywords = keywords
		self.rating = rating
		self.rating_count = rating_count
		self.category = category
		self.cuisine = cuisine
		self.soup = soup

class Users_Recommendations(db.Model):
	__tablename__='user_recommendations'
	_id=db.Column("id", db.Integer, primary_key=True)
	user=db.Column("user", db.Text)
	recommendation_list=db.Column("recommendation_list", db.Text)

	def __init__(self, user, list):
		self.user = user
		self.recommendation_list = ",".join([str(x) for x in list])


# Miscelanious functions
def import_recipes_table():
	'''
	Importing recipes table from the csv in folder if it is empty.
	returns the number of elements in that table
	'''

	if not Recipes.query.all():
		recipes_df = pd.read_csv('recipes.csv')
		for index, row in recipes_df.iterrows():
			recipe = Recipes(row["title"], row["description"], row['recipeLink'], row['imageLink'], row["keywords"], row["ratingValue"],
							 row["ratingCount"], row["recipeCategory"], row["recipeCuisine"], row['soup'])
			db.session.add(recipe)
			db.session.commit()
		return index
	else:
		return Recipes.query.all()[-1]._id

def get_next_recipe(user):
	'''
	Gets the next recipe for a given user. 
	if the user reaches the end, it just returns the first recipe
	'''
	id = session["recipe_id"]
	if id >= Recipes.query.all()[-1]._id: id = 0
	session["recipe_id"] = id + 1

def get_user_last_recipe(user):
	'''
	If the user has played before, changes recipe_id
	to the last recipe they've classified.
	'''
	if not Users_Classifications.query.filter_by(user=user).all():
		last_recipe_done_by_user = 0
	else:
		last_recipe_done_by_user = Users_Classifications.query.filter_by(user=user).all()[-1].recipe_id

	session["recipe_id"] = last_recipe_done_by_user + 1

def initialize_recommendation_model():
	'''
	Initializes the recommendation algorithm and reads tables into their 
	'''
	
	recommendation = Recommendation_Algorithm()
	recommendation.initialize_tables_from_sql(db.engine, 'recipes')
	recommendation.initialize_model()

	return recommendation

def update_recommendations(conn, user, recommendation):
	'''
	we can maybe make this faster, by using less connections with the db
	'''
	index_list = recommendation.sort_recommended_recipes(conn, user, users_table='user_classifications')
	user_rec = Users_Recommendations(user, index_list)
	db.session.add(user_rec)
	db.session.commit()

db.create_all()
db.session.commit()
num_recipes = import_recipes_table()

recommendation = initialize_recommendation_model()

# DEFINING PAGES
@app.route("/", methods=['POST', 'GET'])
def home():
	if "user" in session:
		user = session["user"]
		recipe_id = session["recipe_id"]
		if request.method == "POST":
			classification = request.form["classification"]

			user_classification = Users_Classifications(
				user, recipe_id, classification)
			db.session.add(user_classification)
			db.session.commit()

			# iteration through recipes
			update_recommendations(db.engine, user, recommendation)
			get_next_recipe(user)

			return redirect(url_for("home"))
		else:
			return render_template('home.html', recipe=Recipes.query.get(recipe_id), title='Home')
	else:
		return redirect(url_for("login"))

@app.route("/login",  methods=['POST', 'GET'])
def login():
	if request.method == "POST":
		session.permanent = True
		user = request.form["usr"]
		session["user"] = user
		get_user_last_recipe(user)
		flash("Login successful!", "info")
		return redirect(url_for("home"))
	else:
		if "user" in session:
			return redirect(url_for("home"))
		else:
			return render_template('login.html', title='Login')

@app.route("/logout")
def logout():
	if "user" in session:
		flash("Logout successful!", "info")
		session.pop("user", None)
		session.pop("recipe_id", None)
	return redirect(url_for("login"))

@app.route("/admin")
def admin():

	return render_template("db.html", title="admin", users=Users_Classifications.query.all())

@app.route("/recipes")
def recipes_page():
	if 'user' in session:
		user = session['user']
		user_query = Users_Recommendations.query.filter_by(user=user).all()

		if not user_query:
			return redirect(url_for('home'))

		else: 
			index_list_string = user_query[-1].recommendation_list.split(",")
			index_list = [int(x) for x in index_list_string]

			return render_template("recipes.html", title="Recipes", recipes=Recipes.query.all(), 
			index_list = index_list)
			
	else:
		return redirect(url_for('login'))

@app.route("/about")
def about():

	return render_template('about.html', title='About')

@app.route("/recommendation")
def rec():


	return render_template('recommendation.html', recommendations=Users_Recommendations.query.all())


if __name__ == '__main__':
	app.run(debug=True)
