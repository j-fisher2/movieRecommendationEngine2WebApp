from flask import Flask, render_template, request, session, redirect, url_for, jsonify
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
api_key = os.getenv('API_KEY')
r=redis.Redis(host='localhost',port=os.getenv("REDIS_PORT"),decode_responses=True)

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
    result=df[df.index==index]["title"].values
    if len(result):
        indexCache.insert(index,result[0])
        return result[0]
    else:
        return "title not found"

def getIndexFromTitle(title):
    if title in titleCache.cache:
        print("cache hit")
        titleCache.update(title)
        return titleCache.cache[title].value
    result=df[df.title==title]["index"].values
    if len(result):
        titleCache.insert(title,result[0])
        return result[0]
    else:
        return "title not found"

@app.route("/poster/<movie>")
def home(movie):
    m=r.get(movie)
    return render_template('home.html',movie=m)

@app.route("/recommendations/")
def recommend():
    pass

@app.route("/result/", methods=['POST'])
def getResult():
    movie=request.form.get("movie")
    poster=get_movie_poster(movie)

    return redirect(url_for('home',movie=movie))

@app.route("/search/",methods=["GET","POST"])
def searchPage():
    return render_template("search.html")

@app.route("/search/recommendations/",methods=["POST"])
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
    minHeap=[[get_movie_poster(i[1]),i[1]] for i in minHeap]
    return render_template('recommendations.html',sources=minHeap)

@app.route("/")
def homePage():
    return render_template('home_page.html')

indexCache=Cache(1000)
titleCache=Cache(1000)
    
if __name__=="__main__":
    app.run(debug=True)