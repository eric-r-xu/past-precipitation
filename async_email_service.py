from flask import Flask
import asyncio
from flask_mail import Mail, Message
import pandas as pd
import logging
import requests
import time
import pytz
from local_settings import *
from datetime import timedelta, datetime
import gc
import pymysql
import warnings

warnings.filterwarnings("ignore")

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

# async send email function with delay_seconds
async def send_email_with_delay(msg, delay_seconds, app, conn):
    # Wait for the specified delay
    await asyncio.sleep(delay_seconds)
    conn.send(msg)


async def timetz(*args):
    return datetime.now(tz).timetuple()


# log in PST
tz = pytz.timezone("US/Pacific")
logging.Formatter.converter = timetz

logging.basicConfig(
    filename="/logs/async_email_service.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    datefmt=f"%Y-%m-%d %H:%M:%S ({tz})",
)


# connect to sql
def getSQLConn(host, user, password):
    return pymysql.connect(host=host, user=user, passwd=password, autocommit=True)

# convert Kelvin to Fahrenheit
def K_to_F(degrees_kelvin):
    return int((float(degrees_kelvin) * (9 / 5)) - 459.67)


mysql_conn = getSQLConn(MYSQL_AUTH["host"], MYSQL_AUTH["user"], MYSQL_AUTH["password"])


# run query
def runQuery(mysql_conn, query):
    with mysql_conn.cursor() as cursor:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            cursor.execute(query)            
            
            
async def main(cityIDset, email_service, app, mysql_conn, city_dict):
    # today's date
    dateFact = datetime.now().strftime("%Y-%m-%d")
    logging.info('dateFact=%s' % (dateFact))
    # tomorrow's date
    tomorrow = str((datetime.now() + timedelta(1)).strftime("%Y-%m-%d"))
    logging.info('tomorrow=%s' % (tomorrow))
    async_email_tasks = []
    
    # truncate table tblFactCityWeather with current data and data older than 10 days
    query = """DELETE from klaviyo.tblFactCityWeather where dateFact=CURRENT_DATE or dateFact<date_sub(CURRENT_DATE, interval 10 day) """
    runQuery(mysql_conn, query)
    logging.info("finished truncate table step")
    for _i, cityID in enumerate(cityIDset):
        logging.info(f"cityID={cityID}")
        # current weather api call
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/weather?id=%s&appid=%s"
            % (cityID, OPENWEATHERMAP_AUTH["api_key"])
        )
        obj = r.json()
        today_weather = "-".join(
            [obj["weather"][0]["main"], obj["weather"][0]["description"]]
        )
        today_max_degrees_F = K_to_F(obj["main"]["temp_max"])
        time.sleep(0.5)  # reduce cadence of api calls
        # forecast weather api call
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast?id=%s&appid=%s"
            % (cityID, OPENWEATHERMAP_AUTH["api_key"])
        )
        obj = r.json()
        tmrw_objs = [x for x in obj["list"] if x["dt_txt"][0:10] == tomorrow]
        tomorrow_max_degrees_F = K_to_F(
            max([tmrw_obj["main"]["temp_max"] for tmrw_obj in tmrw_objs])
        )
        query = (
            "INSERT INTO klaviyo.tblFactCityWeather(city_id, dateFact, today_weather, today_max_degrees_F, \
        tomorrow_max_degrees_F) VALUES (%i, '%s', '%s', %i, %i)"
            % (
                cityID,
                dateFact,
                today_weather,
                today_max_degrees_F,
                tomorrow_max_degrees_F,
            )
        )
        runQuery(mysql_conn, query)
 
    logging.info("finished weather api service for all cities")
    
    tblDimEmailCity = pd.read_sql_query(
        """SELECT email, city_id FROM klaviyo.tblDimEmailCity""", con=mysql_conn
    )

    city_id_set = set(tblDimEmailCity["city_id"])
    # logging.info(f"city_id_set = {city_id_set}")
    city_id_string = str(city_id_set).replace("{", "").replace("}", "")
    tfcw_df = pd.read_sql_query(
        f"""SELECT city_id, today_weather, today_max_degrees_F, tomorrow_max_degrees_F FROM klaviyo.tblFactCityWeather where dateFact=CURRENT_DATE and city_id in ({city_id_string}) """,
        con=mysql_conn,
    )
    tblFactCityWeather_dict = dict()
    zipped_array = zip(
        tfcw_df["city_id"],
        tfcw_df["today_weather"],
        tfcw_df["today_max_degrees_F"],
        tfcw_df["tomorrow_max_degrees_F"],
    )
    for city_id, today_weather, today_F, tomorrow_F in zipped_array:
        logging.info(f"city_id={city_id}")
        tblFactCityWeather_dict[city_id] = [
            str(today_weather).lower(),
            int(today_F),
            int(tomorrow_F),
        ]
    for city_id in city_id_set:
        gc.collect()
        # NYC, Boston, Reading, use 3 hour delay
        if int(city_id) in [5392171, 4930956, 4948462]:
            delay_seconds = 10800
        elif int(city_id) in [4683416, 4671240, 4719457, 4705349, 4726206, 4684888, 2646507, 4693003, 5525577, 4693003, 4700168]:
            delay_seconds = 7200
        else:
            delay_seconds = 0

        # find set of recipients per city id
        _tblDimEmailCity = tblDimEmailCity[tblDimEmailCity["city_id"] == city_id]
        _tblDimEmailCity = _tblDimEmailCity.reset_index(drop=True)
        recipients = set(_tblDimEmailCity["email"])
        logging.info("recipients = %s" % recipients)
        today_weather = tblFactCityWeather_dict[city_id][0]
        today_F = tblFactCityWeather_dict[city_id][1]
        tomorrow_F = tblFactCityWeather_dict[city_id][2]
        # subject_value + gif_link logic
        precipitation_words = ["mist", "rain", "sleet", "snow", "hail"]
        sunny_words = ["sunny", "clear"]
        if any(x in today_weather for x in sunny_words):
            logging.info("sunny")
            subject_value = "It's nice out! Enjoy a discount on us."
            gif_link = "https://media.giphy.com/media/nYiHd4Mh3w6fS/giphy.gif"
        elif today_F >= tomorrow_F + 5:
            print("warm")
            subject_value = "It's nice out! Enjoy a discount on us."
            gif_link = "https://media.giphy.com/media/nYiHd4Mh3w6fS/giphy.gif"
        elif any(x in today_weather for x in precipitation_words):
            logging.info("precipitation")
            subject_value = "Not so nice out? That's okay, enjoy a discount on us."
            gif_link = "https://media.giphy.com/media/1hM7Uh46ixnsWRMA7w/giphy.gif"
        elif today_F + 5 <= tomorrow_F:
            logging.info("cold")
            subject_value = "Not so nice out? That's okay, enjoy a discount on us."
            gif_link = "https://media.giphy.com/media/26FLdaDQ5f72FPbEI/giphy.gif"
        else:
            logging.info("other")
            subject_value = "Enjoy a discount on us."
            gif_link = "https://media.giphy.com/media/3o6vXNLzXdW4sbFRGo/giphy.gif"
        with app.app_context():
            with email_service.connect() as conn:
                logging.info(f"recipients = {recipients}")
                for recipient in recipients:
                    msg = Message(
                        subject_value,
                        recipients=[recipient],
                        sender=GMAIL_AUTH["mail_username"],
                    )
                    msg.html = """ %s - %s degrees F - %s <br><br><img src="%s" \
                    width="640" height="480"> """ % (
                        city_dict[str(city_id)],
                        today_F,
                        today_weather,
                        gif_link,
                    )
                    logging.info(f"recipient = {recipient}")
                    try:
                        email_task = asyncio.create_task(
                            send_email_with_delay(
                                msg=msg,
                                delay_seconds=delay_seconds,
                                app=app,
                                conn=conn,
                            )
                        )
                        async_email_tasks.append(email_task)
                    except:
                        logging.error(
                            f"""failed to schedule email to {recipient} with delay of {delay_seconds} seconds """
                        )
                    
        await asyncio.gather(*async_email_tasks)   
    logging.info("finished email service")





asyncio.run(main(cityIDset, email_service, app, mysql_conn, city_dict))
