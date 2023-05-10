from flask import Flask
from flask_mail import Mail, Message
import pandas as pd
import logging
import requests
import time
from local_settings import *
import datetime
import gc
import pymysql
import pytz
import warnings
import initialize_mysql_rain
from initialize_mysql_rain import lat_lon_dict

app = Flask(__name__)

app.config.update(
    dict(
        DEBUG=True,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME=GMAIL_AUTH["mail_username"],
        MAIL_PASSWORD=GMAIL_AUTH["mail_password"],
    )
)

email_service = Mail(app)


def timetz(*args):
    return datetime.datetime.now(tz).timetuple()


# logging datetime in PST
tz = pytz.timezone("US/Pacific")
logging.Formatter.converter = timetz

logging.basicConfig(
    filename="/logs/rain_api.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    datefmt=f"%Y-%m-%d %H:%M:%S ({tz})",
)


# connect to sql
def getSQLConn(host, user, password):
    return pymysql.connect(host=host, user=user, passwd=password, autocommit=True)


mysql_conn = getSQLConn(MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"])


# run query
def runQuery(mysql_conn, query):
    with mysql_conn.cursor() as cursor:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor.execute(query)


def rain_api_service_history_1h_ago(mysql_conn, lat_lon_dict, location_name_filter):
    api_key = OPENWEATHERMAP_AUTH["api_key"]
    for location_name in [each for each in lat_lon_dict.keys()]:
        if location_name == location_name_filter:
            logging.info(f"starting api call for {location_name}")
            lat, lon = (
                lat_lon_dict[location_name]["lat"],
                lat_lon_dict[location_name]["lon"],
            )
            requested_dt = int(time.time()) - 3600
            # https://api.openweathermap.org/data/3.0/onecall/timemachine?lat=37.493&lon=-122.173&dt=1683341200&appid=a4b3d4b6c2fb1eee3b2b42d41d264c9b
            api_link = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={dt}&appid={api_key}"
            r = requests.get(api_link)
            logging.info(f"finished getting {api_link} data")
            api_result_obj = r.json()
            rain_1h, rain_3h, dt = 0, 0, api_result_obj['data'][0]['dt']
            try:
                rain_1h = api_result_obj['data'][0]['rain']['1h']
            except:
                pass
            try:
                rain_3h = api_result_obj['data'][0]['rain']['3h']
            except:
                pass

            query = (
                "INSERT INTO rain.tblFactLatLon(dt, requested_dt, location_name, lat, lon, rain_1h, rain_3h) VALUES (%i, %i, '%s', %.3f, %.3f, %.1f, %.1f)"
                % (
                    dt,
                    requested_dt,
                    location_name,
                    lat,
                    lon,
                    rain_1h,
                    rain_3h,
                )
            )
            logging.info("query=%s" % (query))
            runQuery(mysql_conn, query)
            logging.info(
                "%s - %s - %s - %s - %s - %s - %s"
                % (
                    dt,
                    requested_dt,
                    location_name,
                    lat,
                    lon,
                    rain_1h,
                    rain_3h,
                )
            )


def rain_api_service(mysql_conn, lat_lon_dict):
    api_key = OPENWEATHERMAP_AUTH["api_key"]
    for location_name in [each for each in lat_lon_dict.keys()]:
        logging.info(f"starting api call for {location_name}")
        lat, lon = (
            lat_lon_dict[location_name]["lat"],
            lat_lon_dict[location_name]["lon"],
        )
        api_link = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
        r = requests.get(api_link)
        logging.info(f"finished getting {api_link} data")
        requested_dt = int(time.time())
        api_result_obj = r.json()
        rain_1h, rain_3h, dt = 0, 0, api_result_obj["dt"]
        try:
            rain_1h = api_result_obj["rain"]["1h"]
        except:
            pass
        try:
            rain_3h = api_result_obj["rain"]["3h"]
        except:
            pass

        query = (
            "INSERT INTO rain.tblFactLatLon(dt, requested_dt, location_name, lat, lon, rain_1h, rain_3h) VALUES (%i, %i, '%s', %.3f, %.3f, %.1f, %.1f)"
            % (
                dt,
                requested_dt,
                location_name,
                lat,
                lon,
                rain_1h,
                rain_3h,
            )
        )
        logging.info("query=%s" % (query))
        runQuery(mysql_conn, query)
        logging.info(
            "%s - %s - %s - %s - %s - %s - %s"
            % (
                dt,
                requested_dt,
                location_name,
                lat,
                lon,
                rain_1h,
                rain_3h,
            )
        )
    return logging.info("finished calling weather api and updating mysql")


logging.info('calling v3.0 weather api')
# rain 3.0 historical api service (backfill Bedwell Bayfront Park only for 1 hour ago)
rain_api_service_history_1h_ago(mysql_conn, lat_lon_dict, "Bedwell Bayfront Park")

logging.info('calling v2.5 weather api')
# rain 2.5 api service
rain_api_service(mysql_conn, lat_lon_dict)
