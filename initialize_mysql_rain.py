import pymysql
import warnings
import pandas as pd
import datetime
import pytz
from local_settings import *
import logging

load_initial_data = False

lat_lon_dict = {
    "Hilo, Hawaii": {"lat": 19.724, "lon": -155.087},
    "Bedwell Bayfront Park": {"lat": 37.493, "lon": -122.173},
    "Urbana, Illinois": {"lat": 40.113, "lon": -88.211},
    "Lake Quannapowitt": {"lat": 42.514, "lon": -71.078},
    "Death Valley, CA": {"lat": 36.505, "lon": -117.079},
    "Mount Diablo State Park": {"lat": 37.882, "lon": -121.914},
    "Yosemite National Park": {"lat": 37.865, "lon": -119.538},
}


location_names = [x for x in lat_lon_dict.keys()]

# connect to sql
def getSQLConn(host, user, password):
    return pymysql.connect(host=host, user=user, passwd=password, autocommit=True)


createSchema = "CREATE SCHEMA IF NOT EXISTS rain;"

createTblFactLatLon = """CREATE TABLE IF NOT EXISTS rain.tblFactLatLon
    (`dt` INT(11) NOT NULL COMMENT 'unixtimestamp of last api data update',
    `requested_dt` INT(11) NOT NULL COMMENT 'unixtimestamp of last api data request',
    `location_name` VARCHAR(255) NOT NULL COMMENT 'label given for latitude longitude coordinate (e.g. Bedwell Bayfront Park)',
    `lat` DECIMAL(7,3) SIGNED NOT NULL COMMENT 'latitude coordinate',
    `lon` DECIMAL(7,3) SIGNED NOT NULL COMMENT 'longitude coordinate',
    `rain_1h` DECIMAL(5,1) NOT NULL COMMENT 'mm rainfall in last hour',
    `rain_3h` DECIMAL(5,1) NOT NULL COMMENT 'mm rainfall in last 3 hours', 
    PRIMARY KEY (`dt`,`lat`,`lon`,`requested_dt`)) 
    ENGINE=InnoDB DEFAULT CHARSET=latin1;"""

mysql_conn = getSQLConn(MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"])

with mysql_conn.cursor() as cursor:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cursor.execute(createSchema)
        cursor.execute(createTblFactLatLon)
        
 # run query
def runQuery(mysql_conn, query):
    with mysql_conn.cursor() as cursor:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor.execute(query)


def unixtime_to_pacific_datetime(unixtime_timestamp):
    # Create a timezone object for the Pacific timezone
    pacific_timezone = pytz.timezone("US/Pacific")
    # Convert the Unix timestamp to a datetime object in UTC timezone
    utc_datetime = datetime.datetime.utcfromtimestamp(unixtime_timestamp)

    # Convert the UTC datetime object to the Pacific timezone
    output = pacific_timezone.localize(utc_datetime).astimezone(pacific_timezone)
    return str(output)


if load_initial_data == True:
    df = pd.read_csv("initial_data.csv").fillna(0)
    requested_dt = 1683435668
    for index, row in df.iterrows():
        query = (
            "INSERT IGNORE INTO rain.tblFactLatLon(dt, requested_dt, location_name, lat, lon, rain_1h, rain_3h) VALUES (%i, %i, '%s', %.3f, %.3f, %.1f, %.1f)"
            % (
                row["dt"],
                requested_dt,
                row["city_name"],
                row["lat"],
                row["lon"],
                row["rain_1h"],
                row["rain_3h"],
            )
        )
        logging.info("query=%s" % (query))
        runQuery(mysql_conn, query)
        logging.info(
            "%s - %s - %s - %s - %s - %s - %s"
            % (
                row["dt"],
                requested_dt,
                row["city_name"],
                row["lat"],
                row["lon"],
                row["rain_1h"],
                row["rain_3h"],
            )
        )
    logging.info("finished preload")
