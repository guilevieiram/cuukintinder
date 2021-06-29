# recipe_tinder
Recomendation model using cosines-similarity matrices on a tinder-like approach for item-item recommendation.

## recomendation_model.py
Python file containing the Recommendation Algorithm
This algorithm selects the best match for a user and a recipe inside a given lesson. Lessons are compilations of recipes regarding a given theme (e.g. knife skills)

## Files
- recipes_clean.csv: preprocessed version of recipes, containing only the useful information.
- lessons.csv: relation of what recipes are in each lesson
- users.csv: user classification (0,1) for given recipes

## Next steps
- User classification must come from a tinder-like app. Probably will be done with Flask and ran on a heroku server.


