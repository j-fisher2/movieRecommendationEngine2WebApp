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
    genres=row[2].split(" ")
    for genre in genres:
        all_genres.add(genre)

all_genres.add("Science Fiction")
all_genres.remove("Science")
all_genres.remove('genres')
all_genres.remove("Movie")

print(all_genres)

for g in all_genres:
    if not len(g):
        continue
    query="INSERT INTO genres(name) VALUES(%s)"
    values=(g,)
    cursor.execute(query,values)

connection.commit()
