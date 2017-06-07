import foursquare
import re
import os

class Analyzer(object):
    def __init__(self, config):
        self.config = config
        apiconf = config['api']
        self.client = foursquare.Foursquare(
            client_id=apiconf['id'],
            client_secret=apiconf['secret'],
            redirect_uri=apiconf['callback']
        )
        self.updated = '20170606'

        self.regexes = {n: re.compile(r, re.IGNORECASE) for n, r in config['search']['regex'].items()}

        if(os.path.isfile('token')):
            access_token = open('token', 'r').read()
            self.client.set_access_token(access_token)

    def get_auth_uri(self):
        return self.client.oauth.auth_url()

    def authorize(self, token):
        access_token = self.client.oauth.get_token(token)
        self.client.set_access_token(access_token)
        outfile = open('token','w')
        outfile.write(access_token)
        outfile.close()

    def crunch(self):
        searchconf = self.config['search']
        cats = ','.join(searchconf['category_id'])
        stops = self.client.venues.search(params={
            'near': searchconf['near'],
            'v': self.updated,
            'categoryId': cats,
            'intent': 'browse',
            'limit': 50,
        })

        venues = {}
        orphans = []
        for s in stops['venues']:
            which = self.getFormat(s['name'])
            if(which):
                if(which not in venues):
                    venues[which] = []
                venues[which].append(s)
            else:
                orphans.append(s)

        return (venues, orphans)

    def getFormat(self, name):
        for n, r in self.regexes.items():
            if(r.match(name)):
                return n

        return None

