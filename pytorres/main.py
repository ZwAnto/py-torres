import os
from itertools import groupby
from typing import Union

import requests
from dotenv import dotenv_values
from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

from pytorres.parser import Parser
from pytorres.utils import aggregate_es_scores, check_es

config = {
    **dotenv_values(),
    **os.environ
}

parsers = {i.name: i for i in Parser.__subclasses__()}

es = Elasticsearch(hosts=config['ES_HOST'])
app = FastAPI()


#     ██████╗ █████╗  ██████╗██╗  ██╗███████╗
#    ██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝
#    ██║     ███████║██║     ███████║█████╗  
#    ██║     ██╔══██║██║     ██╔══██║██╔══╝  
#    ╚██████╗██║  ██║╚██████╗██║  ██║███████╗
#     ╚═════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(config['REDIS_HOST'], encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


#    ███████╗███╗   ██╗██████╗ ██████╗  ██████╗ ██╗███╗   ██╗████████╗███████╗
#    ██╔════╝████╗  ██║██╔══██╗██╔══██╗██╔═══██╗██║████╗  ██║╚══██╔══╝██╔════╝
#    █████╗  ██╔██╗ ██║██║  ██║██████╔╝██║   ██║██║██╔██╗ ██║   ██║   ███████╗
#    ██╔══╝  ██║╚██╗██║██║  ██║██╔═══╝ ██║   ██║██║██║╚██╗██║   ██║   ╚════██║
#    ███████╗██║ ╚████║██████╔╝██║     ╚██████╔╝██║██║ ╚████║   ██║   ███████║
#    ╚══════╝╚═╝  ╚═══╝╚═════╝ ╚═╝      ╚═════╝ ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/es", dependencies=[Depends(check_es(es))])
def es_info():
    return es.info()


#        ██╗███╗   ███╗ ██████╗ ██╗   ██╗██╗███████╗
#       ██╔╝████╗ ████║██╔═══██╗██║   ██║██║██╔════╝
#      ██╔╝ ██╔████╔██║██║   ██║██║   ██║██║█████╗  
#     ██╔╝  ██║╚██╔╝██║██║   ██║╚██╗ ██╔╝██║██╔══╝  
#    ██╔╝   ██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝ ██║███████╗
#    ╚═╝    ╚═╝     ╚═╝ ╚═════╝   ╚═══╝  ╚═╝╚══════╝


@app.get("/movie/detail/{imdbId}", dependencies=[Depends(check_es(es))])
def movie(imdbId):

    es_matches_primary = es.search(
        index="imdb-movie*", 
        query={"bool": {
            "filter": [
                {"bool": {
                    "should": [
                        #{"match": {"imdbId": i}} for i in self.es_scores.keys()
                        {"match": {"imdbId": imdbId}}
                    ]
                }},
                {"match": {"source":"primary"}}
        ]}})
    
    if es_matches_primary['hits']['total']['value'] == 0:
        raise HTTPException(status_code=500, detail=f"No match found using imdbId {imdbId}.")
    else:
        return es_matches_primary['hits']['hits'][0]['_source']


@app.get("/movie/detail/{imdbId}/tmdb")
@cache(expire=60*60*24)
async def movie_tmdb(imdbId: str):

    res = requests.get(f'https://api.themoviedb.org/3/find/{imdbId}?api_key={ config.get("TMDB_API_KEY") }&external_source=imdb_id').json()
    
    if len(res['movie_results']) == 0:
        raise HTTPException(status_code=500, detail=f"No match found with imdbId {imdbId}.")
    else:
        tmdbId = res['movie_results'][0]['id']
        res = requests.get(f'https://api.themoviedb.org/3/movie/{tmdbId}?api_key={ config.get("TMDB_API_KEY") }&language=fr').json()
        return {"success": True, "message": res}


@app.get("/movie/lookup", dependencies=[Depends(check_es(es))])
def movie_lookup(q: str, index: str, year: Union[None, str]=None, parser: Union[None, str]=None):

    if parser is not None:
        q_parsed = parsers[parser](q)
        q = q_parsed.query_string

        if year is None:
            year = q_parsed.PTN.get('year')

    query = {    
        "bool": {
            "must": [
                {"query_string": { "query": q }}
            ]
        }
    }

    if year is not None:
        query['bool']['should'] = [
            {"match": { "year": year }}
        ]

    return aggregate_es_scores(es.search(index="imdb-movie*", query=query))
