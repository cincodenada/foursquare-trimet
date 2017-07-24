import foursquare
import re
import os
import pickle
import copy
from coord import Coord
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
        self.orphans = {}
        self.fieldcounts = defaultdict(Counter)

        # TODO: Make signs work everywhere
        gs = self.config['gridsize']
        ne = Coord(self.config['ne'])
        sw = Coord(self.config['sw'])

        print(frange(sw.flat(), ne.flat(), gs, 100))
        print(frange(sw.flon(), ne.flon(), gs, 100))

        for lat in frange(sw.flat(), ne.flat(), gs, 100):
            for lon in frange(sw.flon(), ne.flon(), gs, 100):
                curne = Coord(lat+gs, lon+gs)
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

                self.venues[venue.genericName()].append(venue)
            else:
                self.orphans[venue['id']] = venue

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

    def getTopValue(self, field, value):
        freq = sorted(self.fieldcounts[field].keys(), key=lambda k: self.fieldcounts[field][k], reverse=True)
        for topv in freq:
            if(self.areSameish(topv, value)):
                return topv


    def areSameish(self, a, b):
        return (self.stripField(a) == self.stripField(b))

    def stripField(self, field):
        if(field):
            return re.sub(r'[^\w\d]+', '', field).lower()
        else:
            return field

    def reportDuplicate(self, master, dupe):
        if(master):
            self.client.venues.flag(dupe, params={
                'problem': 'duplicate',
                'venueId': master,
            })
        else:
            return False

class AnalyzedVenue:
    def __init__(self, pool, venue):
        self.pool = pool
        self.venue = venue
        matched = self.getFormat(venue['name'])
        self.num_matching = defaultdict(lambda: 0)

        if(matched):
            self.matched = True
            (self.parts, self.fields) = matched
        else:
            self.matched = False
            self.fields = {}

    def __getitem__(self, key):
        return self.venue[key]

    def getLatLon(self):
        loc = self['location']
        return Coord(loc['lat'], loc['lng'])

    def getDist(self, venue):
        return self.getLatLon().distance(venue.getLatLon())

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

    def getStandard(self):
        std = self.pool.config['standardize']
        for which, params in std.items():
            if 'match' in params:
                is_match = True
                for k, v in params['match'].items():
                    if not k in self.fields or not self.fields[k].lower() == v.lower():
                        is_match = False
                        continue
                if is_match:
                    return params
            else:
                return params

        return None

    def standardize(self, field, value):
        stdconfig = self.getStandard()
        if field in stdconfig['coalesce']:
            if value is None and field in stdconfig['defaults']:
                return stdconfig['defaults'][field]
            else:
                return self.pool.getTopValue(field, value)

    def getEdit(self, extra_params = {}):
        std = self.getStandard()
        if not std:
            return None
        
        params = {}
        try:
            name = self.standardizedName()
            if(name != self['name']):
                params['name'] = self.standardizedName()
                if not params['name']:
                    return None
        except KeyError:
            pass

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

        params.update(extra_params)
        return params

    def proposeEdit(self, extra_params = {}):
        edits = self.getEdit(extra_params)
        if(edits):
            return self.pool.client.venues.proposeedit(self['id'], params=edits)
        else:
            return False

    def standardizedName(self, fields = None):
        stdfields = {}
        if not fields:
            fields = self.fields

        for f, v in fields.items():
            std = self.standardize(f, v)
            if(std):
                stdfields[f] = std
                self.num_matching[f] = self.pool.fieldcounts[f][std]
            else:
                stdfields[f] = v
        
        return self.getStandard()['format'].format(**stdfields)

    def nameFromStop(self, stop):
        return self.standardizedName({
            'num': stop.id,
            'service': 'TriMet',
        })

    def matchStop(self, stop):
        extra = {
            'name': self.nameFromStop(stop),
            'venuell': stop.getLatLon().csv(5),
        }
        self.proposeEdit(extra)

