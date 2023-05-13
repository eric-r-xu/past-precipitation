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
import argparse
import initialize_mysql_rain


def main(start_input, end_input, location_input, api_call_limit):
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

    # run query
    def runQuery(mysql_conn, query):
        with mysql_conn.cursor() as cursor:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cursor.execute(query)

    from initialize_mysql_rain import lat_lon_dict

    mysql_conn = getSQLConn(
        MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"]
    )
    api_key = OPENWEATHERMAP_AUTH["api_key"]

    logging.info(
        f"start_input: {start_input}, end_input: {end_input}, location_input: {location_input}, api_call_limit: {api_call_limit}"
    )

    if start_input == 0:
        for location_name in [each for each in lat_lon_dict.keys()]:
            logging.info(f"starting api call for {location_name}")
            lat, lon = (
                lat_lon_dict[location_name]["lat"],
                lat_lon_dict[location_name]["lon"],
            )
            api_link = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
            logging.info(f"calling api via {api_link}")
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
        logging.info("Finished last hour with API 2.5 for all locations")

    elif (start_input > 0) and (end_input > start_input):
        api_calls = 0

        for location_name in [each for each in lat_lon_dict.keys()]:
            if location_name == location_input:
                logging.info(f"starting api call for {location_input}")
                lat, lon = (
                    lat_lon_dict[location_name]["lat"],
                    lat_lon_dict[location_name]["lon"],
                )
                # 1 hour increments between ds_start and ds_end
                for dt in range(start_input, end_input, 3600):
                    if api_calls == api_call_limit:
                        logging.error(f"api 3.0 call limit ({api_call_limit}) reached")
                        raise Exception("Stopping script execution")
                    logging.info(f"calling api via {api_link}")
                    api_link = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&appid={api_key}"
                    r = requests.get(api_link)
                    logging.info(f"finished getting {api_link} data")
                    api_calls += 1
                    requested_dt = int(time.time())
                    api_result_obj = r.json()
                    rain_1h, rain_3h, dt = 0, 0, api_result_obj["data"][0]["dt"]
                    try:
                        rain_1h = api_result_obj["data"][0]["rain"]["1h"]
                    except:
                        pass
                    try:
                        rain_3h = api_result_obj["data"][0]["rain"]["3h"]
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

        logging.info("Finished backfill with API 3.0 for {location_input}")
    else:
        logging.error("Improper arguments")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="optional backfill parameters for time frame and location"
    )

    # Optional argument
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

    main(args.start_input, args.end_input, args.location_input, args.api_call_limit)

    logging.info("Ended successfully")
