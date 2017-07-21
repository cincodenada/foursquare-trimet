import cherrypy
import analyze
import yaml
from collections import OrderedDict
from html import escape

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
    def connect(self):
        auth_uri = self.crunch.get_auth_uri()
        raise cherrypy.HTTPRedirect(auth_uri)

    @cherrypy.expose
    def callback(self, code=None):
        self.crunch.authorize(code.encode('utf-8'))
        raise cherrypy.HTTPRedirect('/')

if __name__ == '__main__':
   cherrypy.quickstart(Callback(), '/')
