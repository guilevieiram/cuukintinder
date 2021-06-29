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
    def initialize_tables(self, recipe_path=None, users_path=None):
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

    def initialize_tables_from_sql(self, conn, recipe_table=None):
        if not recipe_table == None:
            self.recipes = pd.read_sql(recipe_table, conn)

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

    def sort_recommended_recipes(self, conn, user, users_table="user_classifications"):
        users = pd.read_sql(users_table, conn)

        '''
        
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
        sorted_indexes = list(np.argsort(score_vector))[::-1]

        return [index + 1 for index in sorted_indexes]



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

