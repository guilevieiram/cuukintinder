from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import pandas as pd 

# Importing recipes table

df = pd.read_csv("recipes.csv")

driver_path = os.path.join(os.getcwd(), 'chromedriver')

driver = webdriver.Chrome(driver_path)

image_links = []

try:
	for index in range(df.shape[0]):
		try:
			url = df.at[index, 'recipeLink']	
			driver.get(url)

			media = WebDriverWait(driver, 10).until(
				EC.presence_of_element_located((By.CLASS_NAME, "recipe-media"))
				)

			images = media.find_elements_by_tag_name("img")
			image = images[0]
			image_links.append(image.get_attribute("src"))

		except:
			print("FUCK AN ERROR!!!")
			image_links.append("")

finally:
	driver.quit()

df['imageLinks'] = image_links
df.to_csv('recipes_with_images.csv')


