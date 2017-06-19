import cherrypy
import analyze
import yaml
from html import escape

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
