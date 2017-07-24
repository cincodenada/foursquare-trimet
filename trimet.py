import csv
from scipy.spatial import KDTree
from numpy import array, hstack
from coord import Coord
from collections import OrderedDict

class StopList(object):
    def __init__(self):
        self.stops = OrderedDict()
        self.tree = None

    def getTree(self):
        if(self.tree is None):
            points = [array(s.point(), float) for s in self.stops.values()]
            self.tree = KDTree(array(points, float))
        return self.tree

    def findNearest(self, point):
        if(isinstance(point, Coord)):
            point = [point.lat, point.lon]

        nearestIdx = self.getTree().query(array(point, float))
        nearestStop = list(self.stops.values())[nearestIdx[1]]
        return nearestStop

    def addStop(self, row):
        newStop = Stop(row)
        self.stops[row['stop_id']] = newStop
        self.tree = None

    def loadCSV(self, csvpath):
        with open(csvpath) as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            for row in reader:
                self.addStop(dict(zip(header, row)))

    def loadLines(self, csvpath):
        with open(csvpath) as csvfile:
            reader = csv.reader(csvfile, delimiter='|')
            for (stop_id, lines) in reader:
                if stop_id in self.stops:
                    self.stops[stop_id].setLines(lines)

    def __getitem__(self, key):
        return self.stops[key]

class Stop(object):
    def __init__(self, csvrow):
        for colname, val in csvrow.items():
            colname = colname.replace('stop_','')
            setattr(self, colname, val)

        self.lines = set()

    def getLatLon(self):
        return Coord(self.lat, self.lon)

    def point(self):
        return (self.lat, self.lon)

    def setLines(self, lines):
        self.lines.update(lines.split(','))
