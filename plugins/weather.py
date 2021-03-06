import requests
 
from cloudbot import hook
from cloudbot.util import web
 
 
class APIError(Exception):
    pass
 
# Define some constants
google_base = 'https://maps.googleapis.com/maps/api/'
geocode_api = google_base + 'geocode/json'
 
wunder_api = "http://api.wunderground.com/api/{}/forecast/geolookup/conditions/q/{}.json"
 
# Change this to a ccTLD code (eg. uk, nz) to make results more targeted towards that specific country.
# <https://developers.google.com/maps/documentation/geocoding/#RegionCodes>
bias = None
 
 
def check_status(status):
    """
    A little helper function that checks an API error code and returns a nice message.
    Returns None if no errors found
    """
    if status == 'REQUEST_DENIED':
        return 'The geocode API is off in the Google Developers Console.'
    elif status == 'ZERO_RESULTS':
        return 'No results found.'
    elif status == 'OVER_QUERY_LIMIT':
        return 'The geocode API quota has run out.'
    elif status == 'UNKNOWN_ERROR':
        return 'Unknown Error.'
    elif status == 'INVALID_REQUEST':
        return 'Invalid Request.'
    elif status == 'OK':
        return None
 
 
def find_location(location):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :return: dict
    """
    params = {"address": location, "key": dev_key}
    if bias:
        params['region'] = bias
 
    json = requests.get(geocode_api, params=params).json()
 
    error = check_status(json['status'])
    if error:
        raise APIError(error)
 
    return json['results'][0]['geometry']['location']
 
 
@hook.on_start
def on_start(bot):
    """ Loads API keys """
    global dev_key, wunder_key
    dev_key = bot.config.get("api_keys", {}).get("google_dev_key", None)
    wunder_key = bot.config.get("api_keys", {}).get("wunderground", None)
 
 
@hook.command("weather", "we")
def weather(text, reply):
    """weather <location> -- Gets weather data for <location>."""
    if not wunder_key:
        return "This command requires a Weather Underground API key."
    if not dev_key:
        return "This command requires a Google Developers Console API key."
 
    # use find_location to get location data from the user input
    try:
        location_data = find_location(text)
    except APIError as e:
        return e
 
    formatted_location = "{lat},{lng}".format(**location_data)
 
    url = wunder_api.format(wunder_key, formatted_location)
    response = requests.get(url).json()
 
    if response['response'].get('error'):
        return "{}".format(response['response']['error']['description'])
 
    #forecast_today = response["forecast"]["simpleforecast"]["forecastday"][0]
    #forecast_tomorrow = response["forecast"]["simpleforecast"]["forecastday"][1]
 
    # put all the stuff we want to use in a dictionary for easy formatting of the output
    weather_data = {
        "place": response['current_observation']['display_location']['full'],
        "conditions": response['current_observation']['weather'],
        "temp_f": response['current_observation']['temp_f'],
        "temp_c": response['current_observation']['temp_c']
    }
 
    # Get the more accurate URL if available, if not, get the generic one.
    if "?query=," in response["current_observation"]['ob_url']:
        weather_data['url'] = web.shorten(response["current_observation"]['forecast_url'])
    else:
        weather_data['url'] = web.shorten(response["current_observation"]['ob_url'])
 
    reply("{place} - \x02Current:\x02 {conditions}, {temp_f}F/{temp_c}C".format(**weather_data))
