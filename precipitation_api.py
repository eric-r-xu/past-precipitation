import argparse
import datetime
import gc
import logging
import pymysql
import pytz
import requests
import time
import warnings

from flask import Flask
from flask_mail import Mail, Message
from local_settings import *
import initialize_mysql_rain

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
INCLUSION_LOCATIONS = ['Bedwell Bayfront Park']

class PrecipitationAPI:
    def __init__(self, start_input, end_input, location_input, api_call_limit):
        self.start_input = start_input
        self.end_input = end_input
        self.location_input = location_input
        self.api_call_limit = api_call_limit
        self.tz = pytz.timezone("US/Pacific")

        logging.Formatter.converter = self.timetz
        logging.basicConfig(
            filename="/logs/precipitation_api.log",
            format="%(asctime)s %(levelname)s: %(message)s",
            level=logging.INFO,
            datefmt=f"%Y-%m-%d %H:%M:%S ({self.tz})",
        )
        
        self.mysql_conn = self.getSQLConn(
            MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"]
        )
        self.api_key = OPENWEATHERMAP_AUTH["api_key"]

        from initialize_mysql_rain import lat_lon_dict
        self.lat_lon_dict = lat_lon_dict

    def timetz(self, *args):
        return datetime.datetime.now(self.tz).timetuple()

    def getSQLConn(self, host, user, password):
        return pymysql.connect(host=host, user=user, passwd=password, autocommit=True)

    def runQuery(self, query):
        with self.mysql_conn.cursor() as cursor:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cursor.execute(query)

    def getWeatherData(self, lat, lon, api_version, requested_dt):
        if api_version == "2.5":
            api_link = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}"
        elif api_version == "3.0":
            api_link = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={(requested_dt-14400)}&appid={self.api_key}"
        else:
            raise ValueError("Unsupported API version")

        logging.info(f"calling api via {api_link}")
        r = requests.get(api_link)
        logging.info(f"finished getting {api_link} data")

        return r.json()

    def parseWeatherData(self, api_result_obj):
        rain_1h, rain_3h, dt = 0, 0, api_result_obj["dt"]
        try:
            rain_1h = api_result_obj["rain"]["1h"]
        except:
            pass
        try:
            rain_3h = api_result_obj["rain"]["3h"]
        except:
            pass

        return rain_1h, rain_3h, dt

def main(args):
    precipitation_api = PrecipitationAPI(args.start_input, args.end_input, args.location_input, args.api_call_limit)
    precipitation_api.run() 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="optional backfill parameters for time frame and location"
    )

    parser.add_argument(
        "-s", "--start_input", type=int, default=0, help="dt_start (e.g. 1683853988)"
    )
    parser.add_argument(
        "-e",
        "--end_input",
        type=int,
        default=int(time.time()),
        help="dt_end (e.g. 1683940388)",
    )
    parser.add_argument(
        "-l",
        "--location_input",
        type=str,
        default="None",
        help="location filter (e.g. Bedwell Bayfront Park)",
    )
    parser.add_argument(
        "-a",
        "--api_call_limit",
        type=int,
        default=90,
        help="api 3.0 api call limit (to prevent charges)",
    )

    args = parser.parse_args()
    main(args)
