import csv
from scipy.spatial import KDTree
from numpy import array, hstack
from coord import Coord
from collections import OrderedDict, defaultdict
import re

class StopList(object):
    def __init__(self):
        self.stops = OrderedDict()
        self.tree = None
        self.lines = OrderedDict()

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
        newStop = Stop(self, row)
        self.stops[row['stop_id']] = newStop
        self.tree = None

    def addLine(self, row):
        newLine = Line(self, row)
        self.lines[row['route_id']] = newLine

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

    def loadLineInfo(self, csvpath):
        with open(csvpath) as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            for row in reader:
                self.addLine(dict(zip(header, row)))

    def __getitem__(self, key):
        return self.stops[key]

    def getLine(self, id):
        return self.lines[id]

class Line(object):
    def __init__(self, parent, csvrow):
        self.parent = parent

        for colname, val in csvrow.items():
            colname = colname.replace('route_','')
            setattr(self, colname, val)

    def getFriendlyName(self):
        return self.short_name if self.short_name else self.long_name

    def getAbbreviated(self):
        if(self.short_name):
            return (None, self.short_name)

        max = re.match('MAX (.*) Line', self.long_name)
        if(max):
            return ('MAX', max.group(1))
        
        psc = re.match('Portland Streetcar - (.*?)( Line)?', self.long_name)
        if(psc):
            return ('Portland Streetcar', psc.group(1))

        return (self.long_name, None)


class Stop(object):
    def __init__(self, parent, csvrow):
        self.parent = parent

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

    def getServedBy(self):
        order = []
        groups = defaultdict(list)
        for line_id in sorted(self.lines, key=lambda s: int(s)):
            line = self.parent.getLine(line_id)
            (group, short) = line.getAbbreviated()
            groups[group].append(short)
            if(group not in order):
                order.append(group)

        parts = []
        for group in order:
            lines = groups[group]

            if(group is None):
                parts.append(('line ' if len(lines) == 1 else 'lines ') + ', '.join(lines))
            elif(len(lines) == 1 and lines[0] is None):
                parts.append(group)
            else:
                parts.append(group + ' ' + self.joinWithAnd(lines))

        dirmatch = re.match('\w+bound', self.desc)
        direction = (dirmatch.group().lower() + ' ') if dirmatch else ''

        return ''.join([direction, self.joinWithAnd(parts)])

    def joinWithAnd(self, parts):
        if(len(parts) == 0):
            return ''
        if(len(parts) == 1):
            return parts[0]
        elif(len(parts) == 2):
            return ' and '.join(parts)
        else:
            return ', '.join(parts[0:-1]) + ', and ' + parts[-1]
