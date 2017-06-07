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
        self.venues = {}
        self.orphans = []

        sconf = self.config['search']
        # TODO: Make signs work everywhere
        gs = sconf['gridsize']
        for lat in range(sconf['sw']['lat'], sconf['ne']['lat'], gs):
            for lon in range(sconf['ne']['lon'], sconf['sw']['lon'], gs):
                ne = ','.join([lat+gs, lon])
                sw = ','.join([lat, lon+gs])
                self.subcrunch(ne, sw)

        return (self.venues, self.orphans)

    def subcrunch(self, ne, sw):
        print("Checking grid from {} to {}...".format(ne, sw))
        searchconf = self.config['search']
        cats = ','.join(searchconf['category_id'])
        stops = self.client.venues.search(params={
            'near': searchconf['near'],
            'v': self.updated,
            'categoryId': cats,
            'intent': 'browse',
            'limit': 50,
        })

        for s in stops['venues']:
            which = self.getFormat(s['name'])
            if(which):
                if(which not in self.venues):
                    self.venues[which] = []
                self.venues[which].append(s)
            else:
                self.orphans.append(s)

    def getFormat(self, name):
        for n, r in self.regexes.items():
            if(r.match(name)):
                return n

        return None

