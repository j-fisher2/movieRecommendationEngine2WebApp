import csv
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

all_genres=set()

db_config={
    "host":"localhost",
    "user":os.getenv("SQL_USER"),
    "password":os.getenv("SQL_PASS"),
    "database":os.getenv("SQL_DB")
}

try:
    connection=mysql.connector.connect(**db_config)
    if connection.is_connected():
        print("successful connection")
    
except:
    print("error")

cursor=connection.cursor()

f=open('movie_dataset.csv','r',encoding='utf-8')
datareader=csv.reader(f)


for row in datareader:
    if row[0]=="index":
        continue
    genres=row[2].split(" ")
    for genre in genres:
        all_genres.add(genre)

all_genres.add("Science Fiction")
all_genres.remove("Science")
all_genres.remove("Fiction")
all_genres.remove("Movie")

for g in all_genres:
    if not len(g):
        continue
    query="INSERT INTO genres(name) VALUES(%s)"
    values=(g,)
    cursor.execute(query,values)

#be mindful of the order in which genres are inserted into DB, id's may vary

genre_ids={"Romance":5,"Mystery":9,"Adventure":3,"Documentary":20,"Action":13,"Western":10,"Comedy":19,"Horror":8,"History":18,"Animation":4,"TV":1,"Thriller":2,"Drama":11,"Crime":12,"Fantasy":6,"Music":17,"Foreign":15,"Science Fiction":7,"Family":14,"War":16}

for row in datareader:
    if row[0]=="index":
        continue
    id,genres=row[0],row[2].split(" ")
    if "Science" in genres and "Fiction" in genres:
        genres.remove("Fiction")
        genres.remove("Science")
        genres.append("Science Fiction")
    for g in genres:
            if g in genre_ids:
                g_id=genre_ids[g]
                query2="INSERT INTO movie_genres(movie_id,genre_id) VALUES(%s,%s)"
                values=(id,g_id)
                cursor.execute(query2,values)

connection.commit()
