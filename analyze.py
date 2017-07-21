import foursquare
import re
import os
import pickle
import copy
from collections import Counter, defaultdict, OrderedDict

def frange(start, end, step, factor):
    return [x/factor for x in range(int(start*factor), int(end*factor), int(step*factor))]

class Coord(object):
    def __init__(self, lat, lon = None):
        if(isinstance(lat, dict)):
            self.lat = lat['lat']
            self.lon = lat['lon']
        else:
            self.lat = lat
            self.lon = lon

    def addBoth(self, deg):
        self.lat += deg
        self.lon += deg
        return self

    def __str__(self):
        return '{:0.2f},{:0.2f}'.format(self.lat, self.lon)


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
        self.fieldcounts = defaultdict(Counter)

        # TODO: Make signs work everywhere
        gs = self.config['gridsize']
        ne = Coord(self.config['ne'])
        sw = Coord(self.config['sw'])

        print(frange(sw.lat, ne.lat, gs, 100))
        print(frange(sw.lon, ne.lon, gs, 100))

        for lat in frange(sw.lat, ne.lat, gs, 100):
            for lon in frange(sw.lon, ne.lon, gs, 100):
                curne = Coord(lat, lon).addBoth(gs)
                cursw = Coord(lat, lon)
                self.subcrunch(curne, cursw)

        return (self.venues, self.orphans)

    def subcrunch(self, ne, sw):
        print("Checking grid from {} to {}...".format(ne, sw))

        stops = self.getQuadrant(ne, sw)

        if(len(stops['venues']) >= self.config['max_results']):
            print("Warning! Found {} venues, consider reducing grid size to get all".format(len(stops['venues'])))

        for s in stops['venues']:
            venue = AnalyzedVenue(self, s)

            if(venue.matched):
                for field, val in venue.fields.items():
                    self.fieldcounts[field][val]+=1

                if(venue.fields['service'] == 'Bus'):
                    print(s['name'])

                self.venues[venue.genericName()].append(venue)
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
            (self.parts, self.fields) = matched
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

    def genericName(self):
        if(self.matched):
            return ' '.join(self.parts.values())
        else:
            return self.venue['name']

    def getEdit(self):
        std = self.pool.config['standardize']
        params = {}
        if(self.standardizedName() != self['name']):
            params['name'] = self.standardizedName()
            if not params['name']:
                return None

        correctPrimary = False
        remove = []
        for c in self['categories']:
            if c['id'] == std['category_id']:
                if('primary' in c and c['primary']):
                    correctPrimary = True
            else:
                remove.append(c['id'])

        if len(remove):
            params['removeCategoryIds'] = ','.join(remove)
        if not correctPrimary:
            params['primaryCategoryId'] = std['category_id']

        return params

    def proposeEdit(self):
        edits = self.getEdit()
        if(edits):
            return self.pool.client.venues.proposeedit(self['id'], params=edits)
        else:
            return False

    def standardizedName(self):
        stdfields = {}
        for f, v in self.fields.items():
            stdfields[f] = v
            if f in self.pool.config['standardize']['coalesce']:
                freq = sorted(self.pool.fieldcounts[f].keys(), key=lambda k: self.pool.fieldcounts[f][k], reverse=True)
                for topf in freq:
                    if(self.areSameish(topf, v)):
                        stdfields[f] = topf
                        break

        return self.pool.config['standardize']['format'].format(**stdfields)

    def areSameish(self, a, b):
        return (self.standardizeField(a) == self.standardizeField(b))

    def standardizeField(self, field):
        if(field):
            return re.sub(r'[^\w\d]+', '', field).lower()
        else:
            return field
