import cherrypy
import analyze
import yaml
from collections import OrderedDict
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
        except:
            self.done = []

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
    def standardize(self, which, approved = None):
        if approved:
            for v in self.venues[which]:
                if v['id'] in approved:
                    print("Proposing edit for venue {}...".format(v['id']))
                    result = v.proposeEdit()
                    if result:
                        print(result)
                        self.done.append(v['id'])

        pickle.dump(self.done, open('cache/done','wb'))

        venues = self.venues[which]
        print(self.venues.keys())
        out = '<html><body>'
        out += """<style>
tr { height: 1px; }
td { height:100%; min-width: 75px; }
label { display:block; height: 100%; }
input[type="submit"] { position: fixed; top:0.5em; }
body { margin-top: 2.5em; }
tr.warn { background-color: yellow; }
tr.error { background-color: red; }
</style>
"""
        out += '<form action="/standardize/{}" method="POST">'.format(which)
        out += '<input type="submit"/>'
        out += "<table border=\"1\">"
        for v in venues:
            edit = v.getEdit()
            if(edit):
                if v['id'] in self.done:
                    checkbox = '<a href="https://foursquare.com/v/{}">Submitted</a>'.format(v['id'])
                else:
                    checkbox = '<label><input type="checkbox" name="approved" value="{}"></label>'.format(v['id'])
            else:
                checkbox = '<a href="https://foursquare.com/v/{}">No edits</a>'.format(v['id'])


            trclass = ''
            if v.fields['num'] and int(v.fields['num']) < 100:
                trclass = 'warn'
            if v.num_matching['service'] < 10:
                trclass = 'warn'

            out += '<tr class="{}"><td><a href="https://foursquare.com/v/{}">{}</a></td><td>{}</td><td>{}</td></tr>\n'.format(
                trclass,
                v['id'],
                v['name'],
                "<br/>\n".join(["{0} -> <{2}>{1}</{2}>".format(type, after, 'i' if type.find('Category') > -1 else 'b') for type, after in edit.items()]),
                checkbox
            )
        out += "</table></form></body></html>"

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
