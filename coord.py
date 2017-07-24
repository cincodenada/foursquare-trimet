from LatLon23 import LatLon

class Coord(LatLon):
    def __init__(self, lat, lon = None, precision=2):
        self.precision=precision
        if(isinstance(lat, dict)):
            super().__init__(lat['lat'], lat['lon'])
        else:
            super().__init__(lat, lon)

    def setPrecision(self, precision):
        self.precision = precision

    def csv(self, precision=None):
        return ','.join(['{:0.{}f}'.format(float(v), precision or self.precision) for v in [self.lat, self.lon]])
        

    def __str__(self):
        return self.csv()

    def flat(self):
        return float(self.lat)

    def flon(self):
        return float(self.lon)


