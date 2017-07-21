import foursquare
import re
import os
import pickle
from collections import Counter, defaultdict, OrderedDict

def frange(start, end, step, factor):
    return [x/factor for x in range(int(start*factor), int(end*factor), int(step*factor))]


class VenuePool(object):
    def __init__(self, creds, config):
        self.config = config
        self.client = foursquare.Foursquare(
            client_id=creds['id'],
            client_secret=creds['secret'],
            redirect_uri=creds['callback']
        )
        self.updated = '20170606'

        self.regexes = OrderedDict()
        for phase, relist in config['regex'].items():
            print(phase)
            self.regexes[phase] = OrderedDict()
            for n, r in relist.items():
                self.regexes[phase][n] = re.compile(r, re.IGNORECASE)

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
        self.venues = defaultdict(list)
        self.orphans = []
        self.subitems = defaultdict(Counter)

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
            venue = AnalyzedVenue(self, s)

            if(venue.matched):
                for gn, val in venue.groups.items():
                    self.subitems[gn][val]+=1

                if(venue.groups['service'] == 'Bus'):
                    print(s['name'])

                self.venues[venue.genericName()].append(s)
            else:
                self.orphans.append(venue)

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

class AnalyzedVenue:
    def __init__(self, pool, venue):
        self.pool = pool
        self.venue = venue
        matched = self.getFormat(venue['name'])

        if(matched):
            self.matched = True
            (self.parts, self.groups) = matched
        else:
            self.matched = False

    def __getitem__(self, key):
        return self.venue[key]

    def getFormat(self, name):
        tomatch = name
        parts = OrderedDict()
        groups = {}
        for phase, regexes in self.pool.regexes.items():
            for n, r in regexes.items():
                #print("Matching \"{}\" against {}...".format(tomatch, r))
                m = r.match(tomatch)
                if(m):
                    #print("Got it!")
                    break;

            if(m):
                parts[phase] = n
                groups.update(m.groupdict())
                if('remainder' in m.groupdict()):
                    tomatch = groups['remainder']
                else:
                    break
            else:
                return None

        groups.pop('remainder')
        return (parts, groups)

        return None

    def genericName(self):
        if(self.matched):
            return ' '.join(self.parts.values())
        else:
            return self.venue['name']

