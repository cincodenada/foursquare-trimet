.load ./csv
CREATE VIRTUAL TABLE vstops USING csv(filename='/store/data/trimet/gtfs/stops.txt', header=yes);
CREATE VIRTUAL TABLE vstop_times USING csv(filename='/store/data/trimet/gtfs/stop_times.txt', header=yes);
CREATE VIRTUAL TABLE vtrips USING csv(filename='/store/data/trimet/gtfs/trips.txt', header=yes);
CREATE TABLE stops AS SELECT * FROM vstops;
CREATE TABLE stop_times AS SELECT * FROM vstop_times;
CREATE TABLE trips AS SELECT * FROM vtrips;
CREATE INDEX s_sid ON stops(stop_id);
CREATE INDEX st_sid ON stop_times(stop_id);
CREATE INDEX st_tid ON stop_times(trip_id);
CREATE INDEX t_tid ON trips(trip_id);
SELECT stop_id, GROUP_CONCAT(DISTINCT route_id) FROM stops s NATURAL JOIN stop_times st NATURAL JOIN trips t GROUP BY stop_id;
