from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests,os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import heapq
load_dotenv()

app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")
api_key = os.getenv('API_KEY')


df=pd.read_csv("movie_dataset.csv")
cos_similarity=pd.read_csv("cosine_similarity.csv",index_col=None,header=None)
cos_similarity=cos_similarity.values

def get_movie_poster(movie):
    url=f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie}"
    response=requests.get(url)
    if response.status_code==200:
        data=response.json()
        if data["results"]:
            path=data["results"][0]["poster_path"]
            return "https://image.tmdb.org/t/p/"+"w200"+path

def getTitleFromIndex(index):
    result=df[df.index==index]["title"].values
    if len(result):
        return result[0]
    else:
        return "title not found"

def getIndexFromTitle(title):
    result=df[df.title==title]["index"].values
    if len(result):
        return result[0]
    else:
        return "title not found"

@app.route("/")
def home():
    top_movies=["sinister","shrek","cars"]
    top_movies=[get_movie_poster(title) for title in top_movies]
    return render_template('home.html',movies=top_movies)

@app.route("/recommendations/")
def recommend():
    pass

@app.route("/result/", methods=['POST'])
def getResult():
    movie=request.form.get("movie")
    url=f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie}"
    response=requests.get(url)

    if response.status_code==200:
        data=response.json()
        if data["results"]:
            poster_path=data["results"][0]["poster_path"]
            base_url = "https://image.tmdb.org/t/p/"
            size="w200"
            complete=f"{base_url}{size}{poster_path}"
            session['pSource']=complete

    return redirect(url_for('home'))

@app.route("/search/",methods=["GET","POST"])
def searchPage():
    return render_template("search.html")

@app.route("/search/results",methods=["POST"])
def getSimilar():
    movie=request.form.get("movie")
    idx=getIndexFromTitle(movie)
    scores=cos_similarity[idx]
    minHeap,json=[],[]

    for i in range(len(scores)):
        if int(scores[i])==1:
            continue
        if len(minHeap)<=20:
            heapq.heappush(minHeap,[scores[i],getTitleFromIndex(i)])
        else:
            if scores[i]>minHeap[0][0]:
                heapq.heappop(minHeap)
                heapq.heappush(minHeap,[scores[i],getTitleFromIndex(i)])
    minHeap.sort(reverse=True)
    for movie in minHeap:
        json.append(movie[1])
    json=",".join(json)
    return jsonify(json)
    
if __name__=="__main__":
    app.run(debug=True) 