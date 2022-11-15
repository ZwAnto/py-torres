from itertools import groupby
from fastapi import HTTPException


def check_es(es):
    def func():
        try:
            es.info()
        except:
            raise HTTPException(status_code=503, detail="Elasticsearch is unreachable")
    return func

def aggregate_es_scores(matches):

    scores = {(i['_source']['imdbId'], i['_score']) for i in matches['hits']['hits']}
    scores = sorted(scores, key=lambda x: x[0])
    scores = {i: max([j[1] for j in v]) for i ,v in groupby(scores, key= lambda x: x[0])}
    scores = dict(sorted(scores.items(), key=lambda x: -x[1]))

    return scores