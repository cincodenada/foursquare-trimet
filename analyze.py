import foursquare
import re
import os
import pickle
from collections import Counter

def frange(start, end, step, factor):
    return [x/factor for x in range(int(start*factor), int(end*factor), int(step*factor))]


class Analyzer(object):
    def __init__(self, creds, config):
        self.config = config
        self.client = foursquare.Foursquare(
            client_id=creds['id'],
            client_secret=creds['secret'],
            redirect_uri=creds['callback']
        )
        self.updated = '20170606'

        self.regexes = {n: re.compile(r, re.IGNORECASE) for n, r in config['regex'].items()}

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
        self.services = Counter()
        self.hash = Counter()

        # TODO: Make signs work everywhere
        gs = self.config['gridsize']
        print(frange(self.config['sw']['lat'], self.config['ne']['lat'], gs, 100))
        print(frange(self.config['sw']['lon'], self.config['ne']['lon'], gs, 100))

        for lat in frange(self.config['sw']['lat'], self.config['ne']['lat'], gs, 100):
            for lon in frange(self.config['sw']['lon'], self.config['ne']['lon'], gs, 100):
                ne = ','.join([str(x+gs) for x in [lat, lon]])
                sw = ','.join([str(x) for x in [lat, lon]])
                self.subcrunch(ne, sw)

        return (self.venues, self.orphans)

    def subcrunch(self, ne, sw):
        print("Checking grid from {} to {}...".format(ne, sw))

        stops = self.getQuadrant(ne, sw)

        if(len(stops['venues']) >= self.config['max_results']):
            print("Warning! Found {} venues, consider reducing grid size to get all".format(len(stops['venues'])))

        for s in stops['venues']:
            matched = self.getFormat(s['name'])

            if(matched):
                (which, parts) = matched

                self.services[parts[0]]+=1
                self.hash[parts[1]] += 1

                if(which not in self.venues):
                    self.venues[which] = []
                self.venues[which].append(s)
            else:
                self.orphans.append(s)

    def getQuadrant(self, ne, sw):
        path = 'cache/{}_{}'.format(ne, sw)
        if(os.path.isfile(path)):
            return pickle.load(open(path, 'rb'))

        cats = ','.join(self.config['category_id'])
        stops = self.client.venues.search(params={
            'ne': ne,
            'sw': sw,
            'v': self.updated,
            'categoryId': cats,
            'intent': 'browse',
            'limit': 50,
        })

        pickle.dump(stops, open(path,'wb'))
        return stops

    def getFormat(self, name):
        for n, r in self.regexes.items():
            m = r.match(name)
            if(m):
                return (n, m.groups())

        return None

