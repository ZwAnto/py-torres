import os
from datetime import timedelta
from enum import Enum
from itertools import accumulate
from time import sleep
from typing import Union

from dotenv import dotenv_values
from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, HTTPException
from requests_cache import CachedSession
from requests_cache.backends import RedisCache

from pytorres.parser import Parser
from pytorres.utils import aggregate_es_scores, check_es


class TitleType(str, Enum):
    tv = "tv"
    movie = "movie"


config = {
    **dotenv_values(),
    **os.environ
}

parsers = {i.name: i for i in Parser.__subclasses__()}

es = Elasticsearch(hosts=config['ES_HOST'])
app = FastAPI()

def es_get_detail(imdbId, index="imdb-movie*"):
    return es.search(
        index=index, 
        query={ "bool": {
            "filter": [
                {"bool": {
                    "should": [
                        {"match": {"imdbId": imdbId}}
                    ]
                }},
            {"match": {"source":"primary"}}
        ]}
    })


#     ██████╗ █████╗  ██████╗██╗  ██╗███████╗
#    ██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝
#    ██║     ███████║██║     ███████║█████╗  
#    ██║     ██╔══██║██║     ██╔══██║██╔══╝  
#    ╚██████╗██║  ██║╚██████╗██║  ██║███████╗
#     ╚═════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝


backend = RedisCache(host=config['REDIS_HOST'], port=int(config['REDIS_PORT']))
session = CachedSession(
    name='tmdb_cache', 
    backend=backend,
    allowable_codes=(200,),
    allowable_methods=('GET',),
    expire_after=timedelta(days=30),
    )

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


@app.get("/parser/{parser}")
def parse(parser: str, q: str):
    q_parsed = parsers[parser](q)
    return {'q_parsed': q_parsed.query_string, 'PTN': q_parsed.PTN}


#       ██╗███╗   ███╗ ██████╗ ██╗   ██╗██╗███████╗                  ██╗████████╗██╗   ██╗
#      ██╔╝████╗ ████║██╔═══██╗██║   ██║██║██╔════╝                 ██╔╝╚══██╔══╝██║   ██║
#     ██╔╝ ██╔████╔██║██║   ██║██║   ██║██║█████╗      █████╗      ██╔╝    ██║   ██║   ██║
#    ██╔╝  ██║╚██╔╝██║██║   ██║╚██╗ ██╔╝██║██╔══╝      ╚════╝     ██╔╝     ██║   ╚██╗ ██╔╝
#   ██╔╝   ██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝ ██║███████╗              ██╔╝      ██║    ╚████╔╝ 
#   ╚═╝    ╚═╝     ╚═╝ ╚═════╝   ╚═══╝  ╚═╝╚══════╝              ╚═╝       ╚═╝     ╚═══╝  
                                                                                      

@app.get("/{titleType}/detail/{imdbId}", dependencies=[Depends(check_es(es))])
def es_lookup(titleType: TitleType, imdbId: str):
    es_matches_primary = es_get_detail(imdbId,f"imdb-{titleType}*")

    if es_matches_primary['hits']['total']['value'] == 0:
        raise HTTPException(status_code=500, detail=f"No match found using imdbId {imdbId}.")
    else:
        return es_matches_primary['hits']['hits'][0]['_source']


@app.get("/{titleType}/detail/{imdbId}/tmdb")
async def tmdb_lookup(titleType: TitleType, imdbId: str):

    res = session.get(f'https://api.themoviedb.org/3/find/{imdbId}?api_key={ config.get("TMDB_API_KEY") }&external_source=imdb_id').json()
    
    if len(res[f'{titleType}_results']) == 0:
        raise HTTPException(status_code=500, detail=f"No match found with imdbId {imdbId}.")
    else:
        tmdbId = res[f'{titleType}_results'][0]['id']
        res = session.get(f'https://api.themoviedb.org/3/{titleType}/{tmdbId}?api_key={ config.get("TMDB_API_KEY") }&language=fr').json()
        return res


@app.get("/{titleType}/lookup", dependencies=[Depends(check_es(es))])
def title_lookup(titleType: TitleType, q: str, index: str, year: Union[None, str]=None):

    query = {    
        "bool": {
            "must": [
                {"query_string": { "query": q }}
            ]
        }
    }

    if year is not None and year != '':
        query['bool']['should'] = [
            {"match": { "year": year }}
        ]

    return aggregate_es_scores(es.search(index=f"imdb-{titleType}*", query=query))


#       ██╗ █████╗ ███╗   ██╗██╗███╗   ███╗███████╗
#      ██╔╝██╔══██╗████╗  ██║██║████╗ ████║██╔════╝
#     ██╔╝ ███████║██╔██╗ ██║██║██╔████╔██║█████╗  
#    ██╔╝  ██╔══██║██║╚██╗██║██║██║╚██╔╝██║██╔══╝  
#   ██╔╝   ██║  ██║██║ ╚████║██║██║ ╚═╝ ██║███████╗
#   ╚═╝    ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝╚══════╝

@app.get("/{titleType}/detail/{imdbId}/tmdb/season/{season}/episode/{episode}")
async def tmdb_lookup(imdbId: str, season: int, episode: int):

    res = session.get(f'https://api.themoviedb.org/3/find/{imdbId}?api_key={ config.get("TMDB_API_KEY") }&external_source=imdb_id')
    assert res.status_code == 200
    res = res.json()

    if len(res[f'tv_results']) == 0:
        raise HTTPException(status_code=500, detail=f"No match found with imdbId {imdbId}.")

    tmdbId = res[f'tv_results'][0]['id']

    if season == -1:
        
        r_tv = session.get(f'https://api.themoviedb.org/3/tv/{tmdbId}?api_key={ config.get("TMDB_API_KEY") }&language=fr&append_to_response=season')
        assert r_tv.status_code == 200
        data_tv = r_tv.json()

        _ep = 0
        for s in data_tv['seasons']:
            if s['season_number'] == 0:
                continue
            _ep += s['episode_count']
            print(_ep)
            if episode <= _ep:
                break
        season = s['season_number']

    for i in range(season, season+5):
        try:
            r_ep = session.get(f'https://api.themoviedb.org/3/tv/{tmdbId}/season/{i}/episode/{episode}?api_key={ config.get("TMDB_API_KEY") }&language=fr')
            assert r_ep.status_code == 200
            break
        except:
            continue

    return r_ep.json()