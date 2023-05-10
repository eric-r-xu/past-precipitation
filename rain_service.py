###### PACKAGES ######
import pandas as pd
import logging
import warnings
import pymysql
from pytz import timezone
import pytz
import time
import dateutil.parser
import flask
import datetime
from functools import wraps
from flask import Flask, request, Response, render_template
import numpy as np
import math
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import initialize_mysql_rain
from flask_mysqldb import MySQL
from local_settings import *
import initialize_mysql_rain
from initialize_mysql_rain import location_names, lat_lon_dict

##########################


def timetz(*args):
    return datetime.datetime.now(tz).timetuple()


# logging datetime in PST
tz = timezone("US/Pacific")
logging.Formatter.converter = timetz

logging.basicConfig(
    filename="/logs/rain_service.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    datefmt=f"%Y-%m-%d %H:%M:%S ({tz})",
)

app = Flask(__name__)

limiter = Limiter(app, default_limits=["500 per day", "50 per hour"])

app.config["MYSQL_HOST"] = MYSQL_AUTH["host"]
app.config["MYSQL_USER"] = MYSQL_AUTH["user"]
app.config["MYSQL_PASSWORD"] = MYSQL_AUTH["password"]
app.config["MYSQL_DB"] = "rain"

mysql = MySQL(app)


# connect to sql
def getSQLConn(host, user, password):
    return pymysql.connect(host=host, user=user, passwd=password, autocommit=True)


# run query
def runQuery(mysql_conn, query):
    with mysql_conn.cursor() as cursor:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor.execute(query)


mysql_conn = getSQLConn(MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"])


@app.route("/rain")
def rain_home_html():
    return render_template("rain_service.html", location_names=location_names)


@app.route("/rain", methods=(["POST"]))
def rain_gen_html_table():
    i_location_name = str(request.form["i_location_name"])
    i_location_lat, i_location_lon = (
        lat_lon_dict[i_location_name]["lat"],
        lat_lon_dict[i_location_name]["lon"],
    )
    df_pre = pd.read_sql_query(
        f"""
        SELECT  
            MIN(SUBSTR(CONVERT_TZ(FROM_UNIXTIME(dt),'UTC','US/Pacific'),1,13)) AS "First API Update Hour (PST)",
            MAX(SUBSTR(CONVERT_TZ(FROM_UNIXTIME(dt),'UTC','US/Pacific'),1,13)) AS "Last API Update Hour (PST)",
            MAX(CONVERT_TZ(FROM_UNIXTIME(requested_dt),'UTC','US/Pacific')) AS "Last API Request Time (PST)"
        FROM 
            rain.tblFactLatLon 
        WHERE 
            location_name = "{i_location_name}" 
            AND lat = {i_location_lat} 
            AND lon = {i_location_lon}
        """,
        mysql_conn,
    )
    df = pd.read_sql_query(
        f"""
        SELECT  
            location_name AS "Location Name",
            {i_location_lat} AS "Latitude",
            {i_location_lon} AS "Longitude",
            SUBSTR(CONVERT_TZ(FROM_UNIXTIME(dt),'UTC','US/Pacific'),1,13) AS "API Update Hour (PST)",
            MAX(CONVERT_TZ(FROM_UNIXTIME(requested_dt),'UTC','US/Pacific')) AS "API Request Time (PST)",
            MAX(rain_1h) AS "Rainfall (mm) Last 1 hour",
            MAX(rain_3h) AS "Rainfall (mm) Last 3 hours"
        FROM 
            rain.tblFactLatLon 
        WHERE 
            location_name = "{i_location_name}" 
            AND lat = {i_location_lat} 
            AND lon = {i_location_lon} 
            AND (rain_1h > 0 OR rain_3h > 0)
        GROUP BY 
            4
        ORDER BY 
            4 DESC,
            5 DESC
        """,
        mysql_conn,
    )
    return render_template(
        "rain_service_result.html",
        tables=[df_pre.to_html(classes="data"), df.to_html(classes="data")],
        titles=np.concatenate([df_pre.columns.values, df.columns.values]),
    )


# --------- RUN WEB APP SERVER ------------#

# Start the app server on port 1080
app.debug = True
app.run(host="0.0.0.0", port=1080, threaded=False)
