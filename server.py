import cherrypy
import analyze
import yaml
import collections
from html import escape

# Rewire YAML to use OrderedDict
# From https://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts/21048064#21048064
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

class Callback(object):
    def __init__(self):
        self.creds = yaml.safe_load(open('creds.yaml','r'))
        self.config = yaml.safe_load(open('config.yaml','r'))
        self.crunch = analyze.Analyzer(self.creds, self.config)

    @cherrypy.expose
    def index(self):
        (venues, orphans) = self.crunch.crunch()
        outstr = ""
        for n, vl in venues.items():
            outstr += "{}: {}<br/>\n".format(escape(n), len(vl))

        for o in orphans:
            outstr += '<a href="https://foursquare.com/v/{}">{}</a><br/>\n'.format(o['id'], o['name'])

        outstr += "<hr>"
        for s, count in self.crunch.services.items():
            outstr += "{}: {}<br/>\n".format(s, count)

        outstr += "<hr>"
        for s, count in self.crunch.hash.items():
            outstr += "{}: {}<br/>\n".format(s, count)

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
