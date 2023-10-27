import mysql.connector
from dotenv import load_dotenv
import os
import csv
load_dotenv()

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
file='movie_dataset.csv'


with open(file, 'r',encoding='utf-8') as f:
    datareader = csv.reader(f)
    for row in datareader:
        if row[0] == 'index':
            continue

        # Sanitize and format the values
        movie_id = int(row[0])
        title = row[18].replace("'", "''") 
        director = row[23].replace("'", "''")

        query = "INSERT INTO movies(id, title, director) VALUES (%s, %s, %s)"
        values = (movie_id, title, director)

        # Execute the query with the provided values
        cursor.execute(query, values)
    
    #added date column to database table between loops
    for row in datareader:
        if row[0] == 'index':
            continue

        date=row[12]
        if not len(date):
            continue
        idx=row[0]
        values=(date,idx)
        query="UPDATE movies SET release_date=%s WHERE id=%s"
        cursor.execute(query, values)


# Commit the changes to the database
connection.commit()

# Close the cursor and the connection
cursor.close()
connection.close()

