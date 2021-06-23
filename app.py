from flask import Flask, render_template, redirect, url_for, request, session, flash, get_flashed_messages
from datetime import timedelta
from flask.templating import render_template_string
from flask_sqlalchemy import SQLAlchemy

import pandas as pd
import numpy as np
import os

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.utils import shuffle

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Recommendation_Algorithm():
    def __init__(self):
        self.recipes_raw = None
        self.recipes = None
        self.users = None
        self.lessons = None
        self.similarity_matrix = None


    # Main public methods
    def initialize_tables(self, recipe_path=None, users_path=None, lessons_path=None):
        if not recipe_path == None:
            if recipe_path.endswith('.csv'):
                self.recipes_raw = pd.read_csv(recipe_path)
            if recipe_path.endswith('.json'):
                self.recipes_raw = pd.read_json(recipe_path)

        if not users_path == None:
            if users_path.endswith('.csv'):
                self.users = pd.read_csv(users_path)
            if users_path.endswith('.json'):
                self.users = pd.read_json(users_path)

        if not lessons_path == None:
            if lessons_path.endswith('.csv'):
                self.lessons = pd.read_csv(lessons_path)
            if lessons_path.endswith('.json'):
                self.lessons = pd.read_json(lessons_path)

    def initialize_tables_from_sql(self, conn, recipe_table=None, users_table=None):
        if not recipe_table == None:
            self.recipes = pd.read_sql(recipe_table, conn)
        if not users_table == None:
            self.users = pd.read_sql(users_table, conn)

        print(self.recipes.head())

    def get_image_links(self):
        # Web scrapper to get all image links and upload them onto the recipes table using selenium

        # Importing chrome driver
        driver_path = os.path.join(os.getcwd(), 'chromedriver')
        driver = webdriver.Chrome(driver_path)

        # main loop
        image_links = []

        try:
            for index in range(self.recipes.shape[0]):
                try:
                    # Accessing recipe url
                    url = self.recipes.at[index, 'recipeLink']    
                    driver.get(url)

                    # Finding media box
                    media = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "recipe-media"))
                        )

                    # getting image tag and appending to list
                    images = media.find_elements_by_tag_name("img")
                    image = images[0]
                    image_links.append(image.get_attribute("src"))

                except:
                    # Appending nothing to recipes without image
                    image_links.append("")

        finally:
            # Quitting driver
            driver.quit()

        # Appending links to recipe table
        self.recipes['imageLink'] = image_links


    def clean_data(self, ratings_count_treshold=10, ratings_value_treshold=3.0):
        self._clean_recipe_table(ratings_count_treshold, ratings_value_treshold)
        self._clean_users_table()
        self._clean_lessons_table()

    def export_data(self, path):
        # Exporting csv
        self.recipes.to_csv(path, index=False)

    def initialize_model(self):
        # Creating counting matrix (counts all features)
        count_matrix = CountVectorizer(stop_words='english').fit_transform(self.recipes['soup'])

        # Create cosine similarity matrix
        cosine_sim = cosine_similarity(count_matrix, count_matrix)

        # To numpy array
        self.similarity_matrix = np.array(cosine_sim)

    def recommend_by_lesson(self, user, lesson_id):
        users = self.users
        lessons = self.lessons

        # Creating lists for positive classified recipes and for negative classified recipes
        users = users[users['user']==user].drop(columns='user')
        positive_indexes = list(users[users['classification']==1]['recipe_id'])
        negative_indexes = list(users[users['classification']==0]['recipe_id'])

        # Getting lesson recipes
        recipes_ids = list(lessons[lessons['lesson_id']==lesson_id]['recipe_id'])

        # making copy of similarity matrix
        similarity_matrix = self.similarity_matrix

        # Flipping sign of negatives
        similarity_matrix[:,negative_indexes] = -similarity_matrix[:,negative_indexes]

        # Reducing matrix given user evaluated recipes
        similarity_matrix = similarity_matrix[:, positive_indexes + negative_indexes]

        # Reducing matrix given recipes ids
        similarity_matrix = similarity_matrix[recipes_ids,:]

        # Creating score vector for given recipes
        score_vector = similarity_matrix.sum(axis=1)

        # Getting index of best match
        index = recipes_ids[score_vector.argmax()]

        # Getting that recipe name
        name = self.recipes.at[index, 'title']

        return index, name

    def sort_recommended_recipes(self, user):
        users = self.users

        '''
        we may have a bug here, not sure.

        the sql recipes table starts with index 1 and that index is imported in the "id" column
        for the self.recipes dataframe

        here we are using those indexes to sort out the similarity matrix, which uses indexes from 0

        maybe all the classifications are kind of shifted

        sorry future me or someone who is looking at this code right now. my bad.
        '''

        '''
        update: maybe i fixed it by subtracting 1 from each index passed as a user entry
        this works because the recipes df initializes with newly made indexes.
        So we just fix this sqlalchemy bs manually...
        '''

        # Getting positive and negative reviews from user
        users = users[users['user']==user].drop(columns='user')
        positive_indexes = list(users[users['classification']==1]['recipe_id'])
        positive_indexes = [index-1 for index in positive_indexes]
        negative_indexes = list(users[users['classification']==0]['recipe_id'])
        negative_indexes = [index-1 for index in negative_indexes]

        classified_indexes = positive_indexes + negative_indexes

        # making copy of similarity matrix
        similarity_matrix = self.similarity_matrix

        # Flipping sign of negative reviews
        similarity_matrix[:,negative_indexes] = -similarity_matrix[:,negative_indexes]

        # Reducing matrix given user evaluated recipes
        similarity_matrix = similarity_matrix[:, classified_indexes]

        # Creating score vector for given recipes
        score_vector = similarity_matrix.sum(axis=1)

        # Getting indexes that sort score array
        sorted_indexes = list(np.argsort(score_vector))

        # Removing classified recipes
        for recipe_id in classified_indexes:
            sorted_indexes.remove(recipe_id)

        return sorted_indexes



    # Private methods
    def _clean_recipe_table(self, ratings_count_treshold, ratings_value_treshold):
        recipes = self.recipes_raw
        
        # Setting recipe_id as index
        recipes.set_index('id', inplace=True)

        # Dropping duplicates and na values
        recipes.drop_duplicates(inplace=True, subset = ['title', 'description'])
        recipes.dropna(axis='rows', inplace=True, subset=['ratingValue', 'ratingCount'])

        # Fixing rating values
        recipes['ratingValue'] = recipes['ratingValue'].apply(self.get_rating)
        recipes = recipes[recipes['ratingCount']>ratings_count_treshold]
        recipes = recipes[recipes['ratingValue']>ratings_value_treshold]

        # Dropping unuseful columns
        columns = ['recipeType', 'authorType', 'prepTime', 'cookTime', 'serving', 'nutrition', 'suitableForDiet', 'gotImage', 'authorName']
        recipes.drop(columns=columns, inplace=True)

        # Processing columns for soup
        recipes['keywords_merged'] = recipes['keywords'].apply(self.reduce_keywords)
        for feature in ['recipeCategory', 'recipeCuisine']:
            recipes[feature + '_merged'] = recipes[feature].apply(self.reduce_string)

        # Creating soup
        recipes['soup'] = recipes.drop(columns = ['title']).apply(self.create_soup, axis=1)

        # Shuffling recipes
        recipes = shuffle(recipes, random_state=42)

        # Reseting index
        self.recipes = recipes.reset_index(drop=True)

    def _clean_users_table(self):
        self.users[['recipe_id','classification']].astype('int64', copy=False)
        
    def _clean_lessons_table(self):
        self.lessons.astype('int64', copy=False)

    # Miscelanious methods
    def get_rating(self, number):
        string = str(number)[:2]
        rating = float(string)/10
        return rating

    def reduce_string(self, string):
        if type(string) != 'str': string = str(string)
        return string.lower().replace(' ', '')

    def reduce_keywords(self, string):
        str_list = string.split(',')
        reduced = [self.reduce_string(key) for key in str_list]
        return ' '.join(reduced)

    def create_soup(self, table):
        labels = ['recipeCategory_merged', 'recipeCuisine_merged','keywords_merged']
        return ' '.join([table[label] for label in labels])


# STARTING FLASK APP
app = Flask(__name__)
app.secret_key = "hihihihi"
app.permanent_session_lifetime = timedelta(minutes=5)

# CONFIGURING DATA BASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
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

@app.route("/admin")
def admin():
    return render_template("db.html", title="admin", users=Users_Classifications.query.all())

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
    app.run()
