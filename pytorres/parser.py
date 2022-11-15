
from pytorres.regex import RE_CLEANUP, RE_NOISE, RE_COMPRESS
import PTN

class Parser:
    pass

class TorrentParser(Parser):

    name="torrent_parser"

    def __init__(self, file):

        self.file = file
        self.name = ' '.join(file.replace('./', '').strip().split('/')[-2:])
        
        self.__parse()

    def __parse(self):
        self.PTN = PTN.parse(self.name)

        title = self.PTN ['title']
        excess = self.PTN.get('excess', [])

        if isinstance(excess, list):
            excess = ' '.join(excess)
                
        self.parsed_excess = self.__string_cleanup(excess)
        self.parsed_title = self.__string_cleanup(title)
    
    def __string_cleanup(self, s):
        return RE_COMPRESS.sub(' ', RE_CLEANUP.sub('', RE_NOISE.sub('', s))).strip()

    @property
    def query_string(self):
        return ' '.join([self.parsed_title, self.parsed_excess]).strip()
