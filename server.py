import cherrypy
import analyze
import yaml
from collections import OrderedDict, defaultdict
from html import escape
import pickle

# Rewire YAML to use OrderedDict
# From https://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts/21048064#21048064

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

class Callback(object):
    def __init__(self):
        self.creds = ordered_load(open('creds.yaml','r'))
        self.config = ordered_load(open('config.yaml','r'))
        self.crunch = analyze.VenuePool(self.creds, self.config)
        (self.venues, self.orphans) = self.crunch.crunch()
        try:
            self.done = pickle.load(open('cache/done','rb'))
        except Exception:
            self.done = defaultdict(list)

    def startForm(self, action):
        out = '<html><body>'
        out += """<style>
tr { height: 1px; }
td { height:100%; min-width: 75px; }
label { display:block; height: 100%; }
input[type="submit"] { position: fixed; top:0.5em; }
body { margin-top: 2.5em; }
tr.warn { background-color: yellow; }
tr.error { background-color: red; }
.done { display: none; }
</style>
"""
        out += '<form action="{}" method="POST">'.format(action)
        out += '<input type="submit"/>'
        out += "<table border=\"1\">"

        return out

    def endForm(self):
        return "</table></form></body></html>"


    @cherrypy.expose
    def index(self):
        outstr = ""
        types = sorted(self.venues.keys(), key=lambda k: len(self.venues[k]), reverse=True)
        for t in types:
            vl = self.venues[t]
            outstr += "<a href=\"/standardize/{0}\">{0}</a>: {1}<br/>\n".format(escape(t), len(vl))

        for o in self.orphans:
            outstr += '<a href="https://foursquare.com/v/{}">{}</a><br/>\n'.format(o['id'], o['name'])

        for field, vals in self.crunch.fieldcounts.items():
            outstr += "<hr><h2>{}</h2>".format(field)
            valorder = sorted(vals.keys(), key=lambda k: vals[k], reverse=True)
            for s in valorder:
                outstr += "\"{}\": {}<br/>\n".format(s, vals[s])

        return outstr

    @cherrypy.expose
    def dedup(self, dupes = None):
        if(dupes):
            if not isinstance(dupes, list):
                dupes = [dupes]

            for dup in dupes:
                print("Dup:" + dup)
                (master, tail) = dup.split(':')
                rest = tail.split(',')
                for dup_id in rest:
                    self.crunch.reportDuplicate(master, dup_id)
                self.done['dedup'].append(master)

            pickle.dump(self.done, open('cache/done','wb'))

        found = defaultdict(list)
        dups = set()
        for vl in self.venues.values():
            for v in vl:
                try:
                    id = "{} {}".format(v.fields['type'].lower(), v.fields['num'])
                except:
                    id = "stop {}".format(v.fields['num'])

                found[id].append(v)
                if(len(found[id]) > 1):
                    dups.add(id)

        out = self.startForm('/dedup')
        for id in dups:
            best = found[id][0]
            for v in found[id]:
                for stat in ['checkinsCount', 'usersCount', 'tipCount']:
                    if v['stats'][stat] > best['stats'][stat]:
                        best = v
                        continue
                    elif v['stats'][stat] < best['stats'][stat]:
                        continue

            dups = [ v for v in found[id] if v['id'] != best['id'] ]
            dists = [v.getDist(best)*1000 for v in dups]

            trclass = set()
            if(dists):
                if max(dists) > 500.0:
                    trclass.add('error')
                elif max(dists) > 50.0:
                    trclass.add('warn')

            if best['id'] in self.done['dedup']:
                checkbox = '<a href="https://foursquare.com/v/{}">Submitted</a>'.format(best['id'])
                trclass.update(['done','submitted'])
            else:
                checkbox = '<label><input type="checkbox" name="dupes" value="{}:{}"></label>'.format(best['id'], ','.join([v['id'] for v in dups]))

            out += '<tr class="{}"><td><a href="https://foursquare.com/v/{}">{}</a></td><td>{}</td><td>{}</td></tr>\n'.format(
                ' '.join(trclass),
                best['id'],
                best['name'],
                "<br/>\n".join(['<a href="https://foursquare.com/v/{1}">{0}</a> {2:0.2f}m'.format(v['name'], v['id'], v.getDist(best)*1000) for v in dups]),
                checkbox
            )

        out += self.endForm()
        return out

    @cherrypy.expose
    def standardize(self, which, approved = None):
        if approved:
            for v in self.venues[which]:
                if v['id'] in approved:
                    print("Proposing edit for venue {}...".format(v['id']))
                    result = v.proposeEdit()
                    if result:
                        print(result)
                        self.done['standardize'].append(v['id'])
            
            pickle.dump(self.done, open('cache/done','wb'))

        venues = self.venues[which]
        print(self.venues.keys())
        out = self.startForm('/standardize/{}'.format(which))
        for v in venues:
            edit = v.getEdit()
            trclass = set()
            if(edit):
                if v['id'] in self.done['standardize']:
                    checkbox = '<a href="https://foursquare.com/v/{}">Submitted</a>'.format(v['id'])
                    trclass.update(['done','submitted'])
                else:
                    checkbox = '<label><input type="checkbox" name="approved" value="{}"></label>'.format(v['id'])
            else:
                checkbox = '<a href="https://foursquare.com/v/{}">No edits</a>'.format(v['id'])
                trclass.update(['done','noedit'])


            if (not 'type' in v.fields or v.fields['type'].lower() == 'stop') and v.fields['num'] and int(v.fields['num']) < 100:
                trclass.add('warn')
            if v.num_matching['service'] < 10:
                trclass.add('warn')
            if 'service' not in v.fields or v.fields['service'] is None:
                trclass.add('error')

            out += '<tr class="{}"><td><a href="https://foursquare.com/v/{}">{}</a></td><td>{}</td><td>{}</td></tr>\n'.format(
                ' '.join(trclass),
                v['id'],
                v['name'],
                "<br/>\n".join(["{0} -> <{2}>{1}</{2}>".format(type, after, 'i' if type.find('Category') > -1 else 'b') for type, after in edit.items()]),
                checkbox
            )

        out += self.endForm()

        return out

    @cherrypy.expose
    def connect(self):
        auth_uri = self.crunch.get_auth_uri()
        raise cherrypy.HTTPRedirect(auth_uri)

    @cherrypy.expose
    def callback(self, code=None):
        self.crunch.authorize(code.encode('utf-8'))
        raise cherrypy.HTTPRedirect('/')

if __name__ == '__main__':
   cherrypy.quickstart(Callback(), '/')
