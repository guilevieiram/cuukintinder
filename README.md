# Cuukin Tinder

This project goal was to build a tinder for recipes! Where you can like or dislike recipes based on your taste and then see a list of the 50 best recipes for you!

You can start playing in <a href = 'cuukintinder.herokuapp.com'>CuukinTinder</a>.

This was made in colaboration with <a href= "https://www.cuukin.app">Cuukin</a>, a cooking school at your fingertips!

## Frontend

### Tools
The apps frontend was built using HMTL5, CSS3 and Bootstrap. All of this pages templates can be found in the "templates" folder. The recipes and the images were provided by the BBC Foods website  (more on this dataset later).
Most of the design was acquired from <a href="getbootstrap.com">Bootstrap</a>.

### Features
The app is very simple, consisting of a Login page, a main play page, a recipes page (where your recommendations are) and an about page for anyone who is interesting.
- Login: This is a very simple app, so you don't need to register with any password to get access. Just pop in any valid email and you're good to go! All your preferences will be stored in that e-mail account.
- Play: This is the main page. Cards with recipes images, title, description and extra information will appear for you to classify on Yes or No! Doing so will bring you the next recipe. If you are interested in any of those you can access theis link to get full access to the recipe in the bbc website!
- Recipes: This is the results page. Here you'll find listed the 50 recipes who best match your taste, based on what you selected while playing. The more you play the more accurate this will become!
- About: Simply an about page with some more insight on the project and the developer (me). 


## Backend
The app backend is built mainly on Python Flask. It also uses an additionary script for the recommendation algorithm (recommendation_model.py) and the SQLAlchemy framework.

### app.py
This is the main script for the app. It manages sessions, connects with the data base (creating and updating tables through sqlalchemy), loads pages and processess information for the frontend. 
The app uses three diferent tables to store data. Those tables are created and managed via flask-sqlalchemy objects defined in the script. More detail on the tables are given in the next session. 
### recommendation_model.py
This is an additional script that contains the soul of the project: the class Recommendation_Algorithm. The main use of this class is to load a recommendation model based on a recipes table (either from the db of from the recipes.csv) and then make predictions for a given user and its classifications (yesses or nos on each recipe).
The algorithm works with a Cossine Similarity Matrix. <a href="https://www.youtube.com/watch?v=ueKXSupHz6Q">Here</a> you can find a great tutorial on that method!
The overall steps are as followed:

To initialize the model
- Using several caracteristics/columns from the recipes (cuisine, category and keywords), we can define a "soup" column that aggregates all that information. 
- From that soup column, we can use Python's Scikit Learn library to count every feature in each recipe
- With those features, we use a Word2vec approach to calculate a cossine similarity between every two recipes soups.
- Then we construct a Cossine Similarity Matrix that contains on each cell [i,j] a number between 0 and 1 representing the simmilarity between recipes i and j.

After the model is initialized, we can use this matrix to actually calculate recommendations for any given user. We do this as following:
- We get from the data base every classification a given user has made. This could be 0 (disliked) or 1 (liked) for any recipe.
- The columns regarding the recipes a user disliked get their sign flipped ([.3, .23, .003] - > [-.3, -.23, -.003])
- We filter the matrix to get only the columns the user has classified (liked or disliked)
- We sum the rows across those columns, yielding a score vector. This vector has the final score for every recipe given a user.
- Then we just get the sorted indexes of that vector and voilá: The recipes ids from best to worst for a given user!

After this list is generated, it is passed to the frontend, where it is displayed to the user!


## Data Base
The data base is managed inside the app by SQLAlchemy framework on Flask. The storage is done using a Postgresql database served on Amazon's AWS.
The DB scheme is the following:
- recipes: The recipes table, containing title, description, keywords, link, image_link, category, cuisine and soup. It holds all those general informations about the recipes to be used both by the recommendation model and the frontend.
- user_classifications: This table holds the information given by the user with attributes: user_id (the email used in login), recipe_id and classification. The recipe_id is the id of the recipe on the recipes table and the classifiation can be 0 or 1.
- user_recommendations: a table that holds the recipes recommendations for each user in the form of a user_id and a list/string of the recipes ids. THis table is used by the frontend to create the recipes page.

 
## Deployment
This app is deployed in Heroku. The data base was created there as well through an internal application in heroku.
Due to this choice, a couple of extra files had to be created:
- runtime.txt: basically telling what python version are we using
- requirements.txt: a list of all the packages required for the program
- Procfile: this tells heroku what is your main file and how to run it

Be aware you may need to set up a python buildpack to deploy a python based app on heroku

tip: If you are building your app with a virtual environment, you can simply use the command '<pip freeze > requirements.txt>' to make that file!

## Old files
The old_files folder contains every file i used while testing things out and developping the app. 
Most of the data cleaning and data exporting methods from the Recommendation_Algorithm class were only used here.