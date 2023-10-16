import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def combine_features(row):
    return row['keywords']+" "+row['cast']+" "+row['genres']+" "+row['director']

def generateCosineMatrix(df):
    cv=CountVectorizer()
    count_matrix=cv.fit_transform(df['target_features'])
    cosine_sim=cosine_similarity(count_matrix)
    df=pd.DataFrame(cosine_sim)
    output_path="cosine_similarity.csv"
    df.to_csv(output_path,index=False,header=False)

df=pd.read_csv('movie_dataset.csv')
features=['keywords','cast','genres','director']

for feature in features:
    df[feature]=df[feature].fillna('')

df['target_features']=df.apply(combine_features,axis=1)
df.to_csv('content_dataset.csv')

generateCosineMatrix(df)

