import csv
from scipy.spatial import KDTree

class StopList(object):
    def __init__(self):
        self.stops = {}
        self.tree = None

    def getTree(self):
        if(self.tree is None):
            points = [s.point() for s in self.stops.values()]
            self.tree = KDTree(points)
        return self.tree

    def findNearest(self, point):
        return self.getTree().query(point)

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

    def point(self):
        return [self.lat, self.lon]
