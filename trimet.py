import csv
from scipy.spatial import KDTree
from numpy import array, hstack
from LatLon23 import LatLon, Latitude, Longitude
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
        if(isinstance(point, LatLon)):
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

class Stop(object):
    def __init__(self, csvrow):
        for colname, val in csvrow.items():
            colname = colname.replace('stop_','')
            setattr(self, colname, val)

    def getLatLon(self):
        return LatLon(self.lat, self.lon)

    def point(self):
        return (self.lat, self.lon)
