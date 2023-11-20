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
import datetime
from werkzeug.security import generate_password_hash,check_password_hash
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

genre_ids={"Romance":5,"Mystery":9,"Adventure":3,"Documentary":20,"Action":13,"Western":10,"Comedy":19,"Horror":8,"History":18,"Animation":4,"TV":1,"Thriller":2,"Drama":11,"Crime":12,"Fantasy":6,"Music":17,"Foreign":15,"Science Fiction":7,"Family":14,"War":16}

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
    if r.exists(movie):
        print("redis cache hit")
        return r.get(movie)
    url=f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie}"
    response=requests.get(url)
    if response.status_code==200:
        data=response.json()
        if data["results"]:
            path=data["results"][0]["poster_path"]
            if path==None:
                return None
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
        titleCache.insert(title.lower(),result[0])
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
    minHeap=[[get_movie_poster(i[1].lower()),i[1],i[0]] for i in minHeap]
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

def get_release_date(title):
    query="SELECT release_date FROM movies WHERE LOWER(title)=%s"
    values=(title,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    res=cursor.fetchone()[0]
    return res

def filter_movies(top_movies):  #user first likes movies
    #save final list and scores within recommendations table
    user=session['user']
    cursor=mysql.get_db().cursor()
    added=set()
    topRecommendationCache[user]=set()
    top_movies=[i+[get_release_date(i[1])] for i in top_movies]
    for m in top_movies:
        poster,title,sim_score=m[0],m[1],m[2]
        if int(sim_score)==1 or title.lower() in added:
            continue
        id=getIndexFromTitle(title.lower())
        query2="INSERT INTO recommendations(user_id,movie_id,score) VALUES(%s,%s,%s)"
        values=(get_user_id(user),id,sim_score)
        cursor.execute(query2,values)
        if len(topRecommendationCache[session['user']])<20:
            topRecommendationCache[session['user']].add(title.lower())
            added.add(title.lower())
    mysql.get_db().commit()
    return top_movies

def get_user_id(user):
    cursor=mysql.get_db().cursor()
    query="SELECT user_id FROM users WHERE username=%s"
    values=(user,)
    cursor.execute(query,values)
    res=cursor.fetchall()[0]
    return res

def movie_searched(idx):
    query="SELECT * FROM search_frequency WHERE movie_id=%s"
    values=(idx,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    res=cursor.fetchone()
    if res:
        return True
    return False

def update_search_frequency(movie_idx):
    cursor=mysql.get_db().cursor()
    query=""
    values=None
    if movie_searched(movie_idx):
        query="UPDATE search_frequency SET frequency=frequency+1 WHERE movie_id=%s"
        values=(movie_idx,)
    else:
        query="INSERT INTO search_frequency(movie_id,frequency) VALUES(%s,%s)"
        values=(movie_idx,1)
    cursor.execute(query,values)
    mysql.get_db().commit()

def get_user_likes(username,cursor):
    user_id=get_user_id(username)
    query="SELECT movie_id FROM movie_likes WHERE user_id=%s"
    values=(user_id,)
    cursor.execute(query,values)
    res=cursor.fetchall()
    movie_list=set()
    for m in res:
        movie_list.add(m[0])
    return movie_list

def get_top_searches():
    query="SELECT title FROM movies JOIN search_frequency ON movies.id=search_frequency.movie_id ORDER BY search_frequency.frequency DESC LIMIT 20"
    cursor=mysql.get_db().cursor()
    cursor.execute(query)
    results=cursor.fetchall()
    r=[]
    for movie in results:
        r.append(movie[0])
    return r
    
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
    if idx=="title not found":
        session['error']='We\'re sorry, we could not find your movie'
        return redirect(url_for('searchPage'))
    if 'error' in session.keys():
        session.pop('error')
    update_search_frequency(idx)
    minHeap=get_top_recommendations(movie,idx)
    minHeap=[i+[get_release_date(i[1])]for i in minHeap]
    return render_template('recommendations.html',movie=movie,sources=minHeap)

@app.route("/")
def homePage():
    return render_template('home_page.html')

@app.route("/home/<user>")
def user_home(user):
    top_movies=[]
    query="SELECT username,movie_id FROM users JOIN movie_likes ON users.user_id=movie_likes.user_id WHERE users.username=%s"
    values=(user)
    cursor = mysql.get_db().cursor()
    cursor.execute(query,values)
    result=cursor.fetchall()
    if result:
        if session['user'] in topRecommendationCache:  ## user has entries in recommendations
            topMovies=topRecommendationCache[session['user']]
            movie_list=[]
            for movie in topMovies:
                movie_list.append([get_movie_poster(movie.lower()),get_proper_title(movie),get_release_date(movie)])
            return render_template('user_home.html',top_movies=movie_list)
        else:
            seen=set()
            # user has no entries in recommendations
            movie_user_likes=get_user_likes(session['user'],cursor)
            for movie_id in movie_user_likes:
                movie_title=getTitleFromIndex(movie_id)
                min_heap=get_top_recommendations(movie_title,movie_id,True) #[poster,title,sim_score]
                
                for val in min_heap:
                    if val[1] not in seen and val[0] and val[1] not in movie_user_likes:
                        seen.add(val[1])
                        top_movies.append(val)
                top_movies=filter_movies(top_movies)
            return render_template('user_home.html',top_movies=top_movies[1:21])
    else:
        return redirect(url_for('like_movies',user=user))

@app.route('/like_movies/<user>')
def like_movies(user):
    movies=generate_list()
    movies=[[get_movie_poster(movie),get_proper_title(movie)] for movie in movies]
    return render_template('like_movies.html',sources=movies)

@app.route('/initial-liked-movies/<user>',methods=["POST"])
def extract_movies(user):
    checked_values=request.form.getlist('checkboxes')
    query="SELECT user_id FROM users WHERE username=%s"
    values=(user,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    id=cursor.fetchone()[0]
    
    query1="INSERT INTO movie_likes(user_id,movie_id) VALUES(%s,%s)"
    for movie in checked_values:
        movie_id=getIndexFromTitle(movie)
        values=(id,movie_id)
        cursor.execute(query1,values)
        mysql.get_db().commit()
    return redirect(url_for('user_home',user=user))

@app.route("/home/na")
def non_user_home():
    popular_movies=get_top_searches()
    popular_movies=[[get_movie_poster(p),p,get_release_date(p)] for p in popular_movies]
    return render_template('user_home.html',top_movies=popular_movies)

@app.route("/login/")
def login():
    return render_template('login.html')

@app.route("/login/verify",methods=["POST"])
def verify_login():
    username = request.form.get("username")
    passw = request.form.get("pass")

    query = "SELECT password FROM users WHERE username=%s"
    cursor = mysql.get_db().cursor()
    values = (username,)
    cursor.execute(query,values)
    result=cursor.fetchone()
    if result:
        if check_password_hash(result[0],passw):
            if 'error' in session.keys():
                session.pop('error')
            session['user']=username
            return redirect(url_for('user_home',user=username))
    session['error']="invalid login credentials"
    return redirect(url_for('login'))

@app.route("/logout",methods=["GET"])
def logout():
    session.pop('user')
    return redirect(url_for('homePage'))

@app.route("/like-movie",methods=["POST"])
def like_movie():
    movie=request.form.get("movie")
    movie_id=getIndexFromTitle(movie)
    user_id=get_user_id(session['user'])
    query3="SELECT * FROM movie_likes WHERE user_id=%s AND movie_id=%s"
    values3=(user_id,movie_id)
    cursor=mysql.get_db().cursor()
    cursor.execute(query3,values3)
    res=cursor.fetchone()
    if not res:
        query="INSERT INTO movie_likes(user_id,movie_id) VALUES(%s,%s)"
        values=(user_id,movie_id)
        cursor.execute(query,values)
        mysql.get_db().commit()
        return jsonify("success")
    return jsonify("already liked this movie")

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
    hashed_pass=generate_password_hash(password,method='sha256')
    print(hashed_pass)
    cursor = mysql.get_db().cursor()

    query = "SELECT * FROM users WHERE username=%s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()  # Fetch one row
    if result:
        session['error']="Username already exists"
        return redirect(url_for('signupPage'))
    else:
        date_now=datetime.date.today()
        query = "INSERT INTO users (username, password,registration_date) VALUES (%s, %s,%s)"
        values = (username, hashed_pass,date_now)
        try:
            cursor.execute(query, values)
            mysql.get_db().commit()  # Commit the transaction
        except Exception as e:
            print(f"Error: {e}")
            mysql.get_db().rollback()  # Rollback the transaction in case of an error
            return redirect(url_for('signupPage'))
        cursor.close()
        session['user']=username
        if 'error' in session.keys():
            session.pop('error')
        return redirect(url_for('user_home',user=username))

@app.route("/update-user-profile",methods=["POST"])
def update():
    movie=request.form.get('movie')
    user=session['user']
    id=get_user_id(user)
    query="SELECT * FROM recommendations WHERE user_id=%s"
    values=(id,)
    cursor=mysql.get_db().cursor()
    cursor.execute(query,values)
    min_heap=[]
    r=cursor.fetchall()
    seen=set()
    movies_user_has_liked=get_user_likes(user,cursor)
    for row in r:
        id=row[0]
        user_id=row[1]
        movie_id=row[2]
        score=row[3]
        if movie_id not in seen and movie_id not in movies_user_has_liked:
            heapq.heappush(min_heap,[score,movie_id])
            seen.add(movie_id)
    movie_recs=get_top_recommendations(movie,getIndexFromTitle(movie))  #[poster,title,score]
    for movie in movie_recs:
        title=movie[1]
        score=movie[2]
        if len(min_heap)<30 and getIndexFromTitle(title) not in seen and getIndexFromTitle(title) not in movies_user_has_liked:
            if int(score)==1:
                continue
            heapq.heappush(min_heap,[score,getIndexFromTitle(title)])
            seen.add(getIndexFromTitle(title))
        elif len(min_heap)>=30 and score>min_heap[0][0] and getIndexFromTitle(title) not in seen:
            heapq.heappop(min_heap)
            heapq.heappush(min_heap,[score,getIndexFromTitle(title)])
    query="DELETE FROM recommendations WHERE user_id=%s"
    values=(user_id,)
    cursor.execute(query,values)
    mysql.get_db().commit()
    user_id=get_user_id(session['user'])
    query="INSERT INTO recommendations(user_id,movie_id,score) VALUES(%s,%s,%s)"
    #update cache
    min_heap.sort(key=lambda x:x[0],reverse=True)
    topRecommendationCache[session['user']]=set()
    count=0
    for rec in min_heap:
        values=(user_id,rec[1],rec[0])
        if int(score)!=1:
            cursor.execute(query,values)
        if count<20 and int(score)!=1 and rec[1] not in movies_user_has_liked:
            topRecommendationCache[session['user']].add(getTitleFromIndex(rec[1]).lower())
        count+=1
    mysql.get_db().commit()
    return jsonify("success")

@app.route('/find-genres',methods=["POST"])
def get_genres():
    genre=request.form.get('genre')
    year=request.form.get('year')

    query=""
    if year=="":
        query="SELECT movies.title FROM movies JOIN movie_genres ON movies.id=movie_genres.movie_id JOIN genres ON genres.genre_id=movie_genres.genre_id WHERE genres.name=%s LIMIT 100"
        values=(genre,)
        cursor=mysql.get_db().cursor()
        cursor.execute(query,values)
    else:
        y=year.split("-")
        min_year=y[0]+"-01-01"
        max_year=y[1]+"-01-01"
        query="SELECT movies.title FROM movies JOIN movie_genres ON movies.id=movie_genres.movie_id JOIN genres ON genres.genre_id=movie_genres.genre_id WHERE genres.name=%s AND movies.release_date BETWEEN %s AND %s LIMIT 100"
        values=(genre,min_year,max_year)
        cursor=mysql.get_db().cursor()
        cursor.execute(query,values)

    results=cursor.fetchall()
    response={}
    for movie in results:
        title=movie[0]
        path=get_movie_poster(title)
        if not path:
            continue
        response[title]=path
    return jsonify(response)

    
@app.route('/explore')
def explore_page():
    genres=genre_ids.keys()
    return render_template('explore.html',genres=genres)

@app.route('/<user>/liked-movies')
def current_liked_movies(user):
    cursor=mysql.get_db().cursor()
    liked_movies=get_user_likes(user,cursor)
    liked_movies=[[get_movie_poster(getTitleFromIndex(i)),getTitleFromIndex(i),get_release_date(getTitleFromIndex(i))] for i in liked_movies]
    return render_template('liked_movies.html',top_movies=liked_movies)

@app.route("/search-terms/<term>")
def get_search_recommendations(term):
    query="SELECT title from movies JOIN search_frequency ON search_frequency.movie_id=movies.id WHERE LOWER(title) LIKE %s ORDER BY search_frequency.frequency DESC LIMIT 6"
    cursor=mysql.get_db().cursor()
    v=term+'%'
    values=(v,)
    cursor.execute(query,values)
    res=cursor.fetchall()
    res=[r[0] for r in res]
    return jsonify(res)

topRecommendationCache={}
indexCache=Cache(1000)
titleCache=Cache(1000)
    
if __name__=="__main__":
    app.run(debug=True)