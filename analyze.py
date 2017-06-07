import foursquare
import re
import os
import pickle

def frange(start, end, step, factor):
    return [x/factor for x in range(int(start*factor), int(end*factor), int(step*factor))]


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
        if(os.path.isfile('cache')):
            return pickle.load(open('cache', 'rb'))

        self.venues = {}
        self.orphans = []

        sconf = self.config['search']
        # TODO: Make signs work everywhere
        gs = sconf['gridsize']
        print(frange(sconf['sw']['lat'], sconf['ne']['lat'], gs, 100))
        print(frange(sconf['sw']['lon'], sconf['ne']['lon'], gs, 100))

        for lat in frange(sconf['sw']['lat'], sconf['ne']['lat'], gs, 100):
            for lon in frange(sconf['sw']['lon'], sconf['ne']['lon'], gs, 100):
                ne = ','.join([str(x+gs) for x in [lat, lon]])
                sw = ','.join([str(x) for x in [lat, lon]])
                self.subcrunch(ne, sw)

        out = (self.venues, self.orphans)
        pickle.dump(out, open('cache','wb'))
        return out

    def subcrunch(self, ne, sw):
        print("Checking grid from {} to {}...".format(ne, sw))
        searchconf = self.config['search']
        cats = ','.join(searchconf['category_id'])
        stops = self.client.venues.search(params={
            'ne': ne,
            'sw': sw,
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

