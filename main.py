from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flaskext.mysql import MySQL
import requests,os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import heapq
import redis
load_dotenv()

app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")
app.config['MYSQL_DATABASE_USER']=os.getenv("SQL_USER")
app.config['MYSQL_DATABASE_PASSWORD']=os.getenv("SQL_PASS")
app.config["MYSQL_DATABASE_DB"]=os.getenv("SQL_DB")
app.config["MYSQL_DATABASE_HOST"]=os.getenv("HOST")
api_key = os.getenv('API_KEY')
r=redis.Redis(host='localhost',port=os.getenv("REDIS_PORT"),decode_responses=True)
mysql=MySQL(app)

df=pd.read_csv("movie_dataset.csv")
cos_similarity=pd.read_csv("cosine_similarity.csv",index_col=None,header=None)
cos_similarity=cos_similarity.values

class Node:
    def __init__(self,key,value):
        self.key=key
        self.next=None
        self.prev=None
        self.value=value

class Cache:
    def __init__(self,cap):
        self.capacity=cap
        self.cache={}
        self.head=None
        self.tail=None

    def insert(self,key,value):
        if key in self.cache:
            return
        if len(self.cache)==self.capacity:
            self.pop()
        newNode=Node(key,value)
        self.cache[key]=newNode
        if len(self.cache)==1:
            self.head=self.tail=newNode
            return
        self.head.next=newNode
        newNode.prev=self.head
        self.head=self.head.next
    
    def pop(self):
        LRU=self.tail
        self.tail=self.tail.next
        self.tail.prev=None
        del self.cache[LRU.key]
    
    def update(self,key):
        target_node=self.cache[key]
        if self.tail==target_node:
            self.tail=self.tail.next
            if self.tail:
                self.tail.prev=None 
            self.setMRU(target_node)
            return
        if self.head==target_node:
            return 
        prev,next=target_node.prev,target_node.next
        prev.next=next
        next.prev=prev
        self.setMRU(target_node)
    def setMRU(self,node):
        self.head.next=node
        node.prev=self.head
        self.head=node
        self.head.next=None 
        
    
def get_movie_poster(movie):
    print(movie)
    if r.exists(movie):
        print("redis cache hit")
        return r.get(movie)
    url=f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie}"
    response=requests.get(url)
    if response.status_code==200:
        data=response.json()
        if data["results"]:
            path=data["results"][0]["poster_path"]
            complete_path="https://image.tmdb.org/t/p/"+"w200"+path
            r.set(movie,complete_path)
    return r.get(movie)

def getTitleFromIndex(index):
    if index in indexCache.cache:
        indexCache.update(index)
        return indexCache.cache[index].value
    query="SELECT title FROM movies WHERE id=%s"
    values=(index,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    res=cursor.fetchone()
    if res:
        indexCache.insert(index,res[0])
        return res[0]
    else:
        return "title not found"

def getIndexFromTitle(title):
    if title in titleCache.cache:
        print("cache hit")
        titleCache.update(title)
        return titleCache.cache[title].value
    query="SELECT id FROM movies WHERE LOWER(title) =%s"
    values=(title,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    result=cursor.fetchone()
    if result:
        titleCache.insert(title,result[0])
        return result[0]
    else:
        return "title not found"

def get_top_recommendations(movie,idx,collab_recs=False):
    scores=cos_similarity[idx]
    minHeap,json=[],[]
    threshold=21 if not collab_recs else 4
    for i in range(len(scores)):
        if len(minHeap)<threshold:
            heapq.heappush(minHeap,[scores[i],getTitleFromIndex(i)])
        else:
            if scores[i]>minHeap[0][0]:
                heapq.heappop(minHeap)
                heapq.heappush(minHeap,[scores[i],getTitleFromIndex(i)])
    minHeap.sort(reverse=True)
    minHeap=[[get_movie_poster(i[1].lower()),i[1]] for i in minHeap]
    return minHeap

def get_proper_title(lower_title):
    query="SELECT title from movies WHERE LOWER(title)=%s"
    values=(lower_title,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    res=cursor.fetchone()
    if res:
        return res[0]
    return ""

def generate_list():
    titles=['Interstellar','Guardians of the Galaxy','Monsters University','Toy Story','The Avengers','Pearl Harbor','The Perfect Storm','300: Rise of an Empire','The Tourist','The Wolf of Wall Street','Divergent','The Hangover','Bedtime Stories','Grown Ups','The Lion King','Braveheart','The Vow','American Sniper','The Dictator','Marley & Me','Lilo & Stitch']
    titles=[title.lower() for title in titles]
    return titles

@app.route("/poster/<movie>")
def home(movie):
    m=r.get(movie)
    return render_template('home.html',movie=m)

@app.route("/poster/search/", methods=['GET'])
def poster_search():
    return render_template('home.html')

@app.route("/poster/query",methods=["POST"])
def getPoster():
    movie=request.form.get("movie").lower()
    get_movie_poster(movie)
    return redirect(url_for('home',movie=movie))

@app.route("/search/",methods=["GET","POST"])
def searchPage():
    return render_template("search.html")

@app.route("/search/recommendations/",methods=["POST"])
def getSimilar():
    movie=request.form.get("movie").lower()
    idx=getIndexFromTitle(movie)
    minHeap=get_top_recommendations(movie,idx)
    
    return render_template('recommendations.html',movie=movie,sources=minHeap)

@app.route("/")
def homePage():
    return render_template('home_page.html')

@app.route("/home/<user>")
def user_home(user):
    top_movies=[]
    query="SELECT username,movie_id,LOWER(movie_title) FROM users JOIN movie_likes ON users.user_id=movie_likes.user_id WHERE users.username=%s"
    values=(user)
    cursor = mysql.get_db().cursor()
    cursor.execute(query,values)
    result=cursor.fetchall()
    if result:
        count=0
        if r.exists(user):
            topMovies=r.lrange(user,0,-1)
            movie_list=[]
            for movie in topMovies:
                movie_list.append([get_movie_poster(movie.lower()),get_proper_title(movie)])
            return render_template('user_home.html',top_movies=movie_list)
        for username,movie_id, movie_title in result:
            movie_title=movie_title.lower()
            min_heap=get_top_recommendations(movie_title,movie_id,True)
            seen=set()
            for val in min_heap:
                r.rpush(user,val[1])
                if val[1] not in seen and val[0]:
                    val[1]=get_proper_title(val[1])
                    top_movies.append(val)
                    seen.add(val[1])
        return render_template('user_home.html',top_movies=top_movies[1:21])
    else:
        return redirect(url_for('like_movies',user=user))

@app.route('/like_movies/<user>')
def like_movies(user):
    movies=generate_list()
    movies=[[get_movie_poster(movie),movie] for movie in movies]
    return render_template('like_movies.html',sources=movies)

@app.route('/initial-liked-movies/<user>',methods=["POST"])
def extract_movies(user):
    checked_values=request.form.getlist('checkboxes')
    query="SELECT user_id FROM users WHERE username=%s"
    values=(user,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    id=cursor.fetchone()[0]
    
    query1="INSERT INTO movie_likes(user_id,movie_id,movie_title) VALUES(%s,%s,%s)"
    for movie in checked_values:
        movie=movie.lower()
        movie_id=getIndexFromTitle(movie)
        values=(id,movie_id,movie)
        cursor.execute(query1,values)
        mysql.get_db().commit()
    return redirect(url_for('user_home',user=user))

@app.route("/home/na")
def non_user_home():
    return render_template('user_home.html')

@app.route("/login/")
def login():
    return render_template('login.html')

@app.route("/login/verify",methods=["POST"])
def verify_login():
    username = request.form.get("username")
    passw = request.form.get("pass")

    query = "SELECT * FROM users WHERE username=%s AND password=%s"
    cursor = mysql.get_db().cursor()
    values = (username, passw)
    cursor.execute(query,values)
    result=cursor.fetchone()
    if result:
        if 'error' in session.keys():
            session.pop('error')
        session['user']=username
        return redirect(url_for('user_home',user=username))
    else:
        session['error']="invalid login credentials"
        return redirect(url_for('login'))

@app.route("/logout",methods=["GET"])
def logout():
    session.pop('user')
    return redirect(url_for('homePage'))

@app.route("/signup/")
def signupPage():
    return render_template('signup.html')


@app.route("/signup/verify/",methods=["POST"])
def verify_signup():
    username = request.form.get("username")
    password = request.form.get("pass")
    password_confirm=request.form.get("passverify")
    if password!=password_confirm:
        session['error']="password and password confirmation must match"
        return redirect(url_for('signupPage'))
    cursor = mysql.get_db().cursor()

    query = "SELECT * FROM users WHERE username=%s"
    try:
        cursor.execute(query, (username,))
        result = cursor.fetchone()  # Fetch one row
        if result:
            session['error']="Username already exists"
            return redirect(url_for('signupPage'))
        else:
            query = "INSERT INTO users (username, password) VALUES (%s, %s)"
            values = (username, password)
            try:
                cursor.execute(query, values)
                mysql.get_db().commit()  # Commit the transaction
            except Exception as e:
                print(f"Error: {e}")
                mysql.get_db().rollback()  # Rollback the transaction in case of an error
            cursor.close()
            session['user']=username
            if 'error' in session.keys():
                session.pop('error')
            return redirect(url_for('user_home',user=username))
    except Exception as e:
        return jsonify("error occurred")


indexCache=Cache(1000)
titleCache=Cache(1000)
    
if __name__=="__main__":
    app.run(debug=True)