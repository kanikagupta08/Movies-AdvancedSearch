from flask import Flask, request, session, render_template, render_template_string
import search_service
import user_tracking_service
import uuid

app = Flask(__name__)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def index():
    session_id = uuid.uuid1()
    logger.info("Started session : %s", str(session_id))
    session['session_id'] = session_id
    return render_template('search_form.html')


@app.route("/exit")
def exit():
    session.clear()
    return render_template_string('Finishing current session ..')


@app.route("/search", methods=['POST'])
def show_search_results():
    search_query = request.form["search_query"]
    search_filter = None
    if request.form.get('search_filter'):
        search_filter_raw = request.form["search_filter"]
        filter_name, filter_value = search_filter_raw.split("=")
        search_filter = {filter_name:filter_value}
    logger.info("Search Query : %s, Search Filter : %s" % (search_query, search_filter))

    search_input = search_service.SearchInput(query=search_query, filter=search_filter)
    search_output = search_service.search(search_input)

    return render_template('search_results.html', search_output=search_output, search_query=search_query)


@app.route("/track_event", methods=['POST'])
def track_event():
    event_data = request.json
    user_tracking_service.save_event(session['session_id'], event_data)

    return 'OK'


@app.route("/analytics")
def user_analytics():
    events = user_tracking_service.get_user_events()
    return render_template("user_analytics.html", events=events)

if __name__ == "__main__":
    app.secret_key = 'hello'
    app.debug = True
    app.run()