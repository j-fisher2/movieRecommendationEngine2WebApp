#movieRecommendationEngine 

This movie recommendation engine is designed to provide personalized movie suggestions based on user preferences. It allows users to login, sign-up, like movies, search for movies to receieve similar recommendations and more. The engine utilizes Flask for the web application, a MySQL database for user data storage, and various Python libraries for data processing and recommendation generation.

Prerequisites
Before you begin, ensure you have the following installed on your machine:

Python (3.6 or higher)
Flask
MySQL
Redis
Pandas
NumPy
Scikit-Learn
Requests
Dotenv

Installation

Clone the repository

Install Python dependencies:
pip install -r requirements.txt

Set up MySQL database and table that follows the relational schema provided:
Create a MySQL database and user.
Update the .env file with your MySQL database credentials.

Set up Redis:
Install and run Redis on your machine.
Update the .env file with the Redis port.

Obtain API key:
Get an API key from TMDB.
Update the .env file with your API key.

Prepare movie data:
Ensure you have a movie_dataset.csv file with movie data, or that you manually enter movies that match the fields.
Create a cosine similarity matrix based on the given fields found in processData.py

Run the application:
python main.py

Usage
Open your web browser and go to http://localhost:5000.
Create an account or log in if you already have one.
Start exploring personalized movie recommendations based on your preferences.

Relational DB schema
![Screenshot (687)](https://github.com/j-fisher2/movieRecommendationEngine2WebApp/assets/113472699/a090ae82-7dcf-470e-ace8-1231a44573ac)
