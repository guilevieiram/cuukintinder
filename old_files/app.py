from flask import Flask, render_template, redirect, url_for, request, session, flash, get_flashed_messages
from datetime import timedelta
from flask.templating import render_template_string
from flask_sqlalchemy import SQLAlchemy
import pandas as pd

from recommendation_model import Recommendation_Algorithm

# this is a test for linux use

# STARTING FLASK APP
app = Flask(__name__)
app.secret_key = "hihihihi"
app.permanent_session_lifetime = timedelta(minutes=5)

# CONFIGURING DATA BASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# TABLES CLASSES
class Users_Classifications(db.Model):
    __tablename__ = 'users_classifications'
    _id = db.Column("id", db.Integer, primary_key=True)
    user = db.Column("user", db.String(100))
    recipe_id = db.Column("recipe_id", db.Integer)
    classification = db.Column("classification", db.Integer)

    def __init__(self, user, recipe_id, classification):
        self.user = user
        self.recipe_id = recipe_id
        self.classification = classification

class Recipes(db.Model):
    __tablename__='recipes'
    _id = db.Column("id", db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(500))
    recipe_link = db.Column(db.String(100)) 
    image_link = db.Column(db.String(100))
    keywords = db.Column(db.String(100))
    rating = db.Column(db.Float)
    rating_count = db.Column(db.Integer)
    category = db.Column(db.String(50))
    cuisine = db.Column(db.String(50))
    soup = db.Column(db.String(1000))

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
    recommendation.initialize_tables_from_sql(db.engine, 'recipes', 'users_classifications')
    recommendation.initialize_model()

    return recommendation

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
            print("post method activated")
            classification = request.form["classification"]

            user_classification = Users_Classifications(
                user, recipe_id, classification)
            db.session.add(user_classification)
            db.session.commit()

            # iteration through recipes
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

@app.route("/viewdb")
def view_db():
    return render_template("db.html", title="DB", users=Users_Classifications.query.all())

@app.route("/recipes")
def recipes_page():
    if 'user' in session:
        return render_template("recipes.html", title="Recipes", recipes=Recipes.query.all(), 
        index_list = recommendation.sort_recommended_recipes(session['user']))
    else:
        return redirect(url_for('login'))

@app.route("/about")
def about():
    return render_template('about.html', title='About')


if __name__ == '__main__':
    app.run(debug=True)
