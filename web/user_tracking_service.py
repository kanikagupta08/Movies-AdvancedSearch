"""
    Service for tracking various user events on the search site.
"""
from flask import session
import json
#import MySQLdb
import pymysql
db = pymysql.connect(host='localhost', port=3306, user='root', passwd='root', db='movies_search')
#db = MySQLdb.connect("localhost","root","","movies_search" )

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUERY_SEARCH_EVENT = "query_search"
FACET_SEARCH_EVENT = "facet_search"


def save_event(session_id, event_data):
    logger.info("Capturing user event %s for session %s", event_data, session_id)

    event_type = event_data['event_type']
    event_details = json.dumps(event_data)
    cursor = db.cursor()
    sql = "INSERT INTO movies_search.user_session_events(session_id,event_type,event_details,created_at) VALUES('%s', '%s', '%s', now())" % \
          (session_id, event_type, event_details)
    logger.info("SQL => %s", sql)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        logger.error("Failed with error : %s", str(e))
        db.rollback()


def get_user_events():
    sql = "SELECT session_id,event_type,event_details,created_at FROM movies_search.user_session_events"
    cursor = db.cursor()
    rows = []
    try:
        cursor.execute(sql)
        for raw_row in cursor.fetchall():
            row = {}
            row['session_id'] = raw_row[0]
            row['event_type'] = raw_row[1]
            row['event_details'] = raw_row[2]
            row['created_at'] = raw_row[3]

            logger.info(row)

            rows.append(row)
    except Exception as e:
        logger.error("Failed query : %s", str(e))

    return rows
