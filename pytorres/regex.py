import re
import pytorres
from pathlib import Path

exclude_terms = open(Path(pytorres.__path__[0]) / 'conf/exclude_terms').readlines()
exclude_terms = [i.strip() for i in exclude_terms]

RE_CLEANUP =  re.compile('[\[\]\-]')
RE_NOISE = re.compile(f"(?<!\w)(?:{'|'.join(exclude_terms)})(?!\w)", flags=re.IGNORECASE)
RE_COMPRESS = re.compile(' +')


