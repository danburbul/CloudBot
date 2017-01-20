import datetime
import json
from cloudbot import hook
from cloudbot.event import EventType
from html.parser import HTMLParser
from random import choice, sample
from requests import get
from pickle import dump, load
from feedparser import parse
from cloudbot.util.web import try_shorten

BASE_URL = 'https://www.bungie.net/platform/Destiny/'
CACHE = {}
CLASS_TYPES = {0: 'Titan ', 1: 'Hunter ', 2: 'Warlock ', 3: ''}
CLASS_HASH = {671679327: 'Hunter', 3655393761: 'Titan', 2271682572: 'Warlock'}
DISCORD_USER = "katagatame_"
RACE_HASH = {898834093: 'Exo', 3887404748: 'Human', 2803282938: 'Awoken'}
CONSOLES = ['\x02\x033Xbox\x02\x03', '\x02\x0312Playstation\x02\x03']
STAT_HASHES = {144602215: 'Int', 1735777505: 'Disc', 4244567218: 'Str'}
ENEMY_RACE_HASH = {3265589059: 'Hive', 546070638: 'Cabal', 711470098: 'Vex', 1636291695: 'Fallen'}
BOSS_COMBATANT_HASH = {1: 'Pilot Servitor', 2: 'Val Aru\'un', 3: 'Wretched Knight', 4: 'Overmind Minotaur', 5: 'Seditious Mind', 6: 'Noru’usk, Servant of Oryx', 7: 'Keksis the Betrayed', 8: 'Sylok, the Defiled'}
LORE_CACHE = {}
HEADERS = {}
WEAPON_TYPES = ['Super', 'Melee', 'Grenade', 'AutoRifle', 'FusionRifle',
    'HandCannon', 'Machinegun', 'PulseRifle', 'RocketLauncher', 'ScoutRifle',
    'Shotgun', 'Sniper', 'Submachinegun', 'Relic', 'SideArm']
WEAPON_CLASSES = {"PrimaryWeapon": ['HandCannon', 'AutoRifle', 'PulseRifle',
                                    'ScoutRifle'],
                  "SpecialWeapon": ['FusionRifle', 'Shotgun', 'Sniper', 'SideArm'],
                  "HeavyWeapon": ['Machinegun', 'Submachinegun', 'RocketLauncher',
                                  'Relic'],
                  "Ability": ['Super', 'Melee', 'Grenade']}
PVP_OPTS = ['activitiesEntered', 'assists', 'avgKillDistance', 'deaths', 'kills', 'k/d',
    'bestSingleGameKills', 'bestSingleGameScore', 'bestWeapon', 'longestKillSpree',
    'secondsPlayed', 'longestSingleLife', 'orbsDropped', 'precisionKills',
    'precisionRate', 'suicides', 'winRate', 'zonesCaptured']
PVE_OPTS = ['activitiesEntered', 'activitiesCleared', 'avgKillDistance',
    'bestSingleGameKills', 'bestWeapon', 'longestKillSpree', 'deaths', 'kills', 'k/h',
    'secondsPlayed', 'longestSingleLife', 'orbsDropped', 'precisionKills',
    'precisionRate', 'suicides', 'winRate', 'publicEventsCompleted']

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data().replace('\n', '\t')

def string_to_datetime(datetime_as_string):
    try:
        return datetime.datetime.strptime(datetime_as_string,'%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        try:
            return datetime.datetime.strptime(datetime_as_string,'%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            return 'ValueError'

def datetime_to_string(datetime_object):
    return datetime.datetime.strftime(datetime_object,'%Y-%m-%dT%H:%M:%SZ')


def get_user(user_name, console=None):
    '''
    Takes in a username and returns a dictionary of all systems they are
    on as well as their associated id for that system, plus general information
    '''
    platforms = CACHE['links'].get(user_name, {console: user_name})

    if CACHE.get(user_name, None):
        return CACHE[user_name]
    else:
        user_info = {}
        for platform in platforms:
            gamertag = platforms[platform]
            try:
                # Get the Destiny membership ID
                searchResults = get('{}SearchDestinyPlayer/{}/{}/'.format(BASE_URL, platform, gamertag),
                    headers=HEADERS).json()['Response'][0]
                membershipId = searchResults['membershipId']
                displayName = searchResults['displayName']
                # Then get Destiny summary
                characterHash = get(
                    '{}{}/Account/{}/Summary/'
                    .format(BASE_URL, platform, membershipId),
                    headers=HEADERS).json()['Response']['data']
            except:
                return 'A user by the name {} was not found.'.format(gamertag)

            character_dict = {}
            for character in characterHash['characters']:
                character_dict[character['characterBase']['characterId']] = {
                    'level': character['characterLevel'],
                    'LL': character['characterBase']['powerLevel'],
                    'race': RACE_HASH[character['characterBase']['raceHash']],
                    'class': CLASS_HASH[character['characterBase']['classHash']]
                }
            user_dict = {
                'membershipId': membershipId,
                'displayName': displayName,
                'clan': characterHash.get('clanName', 'None'),
                'characters': character_dict
            }
            user_info[platform] = user_dict

        # CACHE[user_name] = user_info
        return user_info if user_info else 'A user by the name {} was not found.'.format(user_name)

def prepare_lore_cache():
    '''
   This function will allow us to do this: LORE_CACHE[name]['cardIntro']
   '''
    lore_base = get('{}/Vanguard/Grimoire/Definition/'.format(BASE_URL),
        headers=HEADERS).json()['Response']['themeCollection']

    global LORE_CACHE
    LORE_CACHE = {}
    grim_tally = 0
    fragments = {}
    siva = {}
    for level1 in lore_base:
        if level1.get('themeId','') == 'Enemies':
            for page in level1['pageCollection']:
                if page['pageId'] == 'BooksofSorrow':
                    for card in page['cardCollection']:
                        fragments[card['cardId']] = card['cardName']
                if page['pageId'] == 'Siva':
                    for card in page['cardCollection']:
                        siva[card['cardId']] = card['cardName']
        for level2 in level1.get('pageCollection', []):
            for card in level2.get('cardCollection', []):
                LORE_CACHE[card['cardName']] = {
                    'cardIntro': card.get('cardIntro', ''),
                   # 'cardDescription': card['cardDescription'],
                    'cardId': card['cardId']
                }
            for card in level2.get('cardBriefs', []):
                grim_tally += card.get('totalPoints', 0)
    CACHE['collections']['grim_tally'] = grim_tally
    CACHE['collections']['fragments'] = fragments
    CACHE['collections']['siva'] = siva

def best_weapon(data):
    best = 0
    weapon = None
    for stat in data:
        if 'weaponKills' in stat:
            if data[stat]['basic']['value'] > best:
                best = data[stat]['basic']['value']
                weapon = stat
    return '{}: {} kills'.format(
        weapon[11:], round(best)) if best else 'You ain\'t got no best weapon!'

def get_weaponclass_total(data, weapon_class):
    # TODO: No Land Beyond, Universal Remote, Sleeper Simulant, etc.
    if weapon_class in WEAPON_CLASSES:
        weaponclass_kills = 0
        for primitive_stat in WEAPON_CLASSES[weapon_class]:
            raw_stat = "weaponKills{0}".format(primitive_stat)
            weaponclass_kills += data[raw_stat]['basic']['value']
        return weaponclass_kills
    else:
        return None

def get_stat(data, stat):
    if stat in WEAPON_TYPES:
        stat = 'weaponKills{}'.format(stat)
    if stat in data:
        return '\x02{}\x02: {}'.format(
            data[stat]['statId'], data[stat]['basic']['displayValue'])
    elif stat.endswith("Percentage"):
        orig_stat = stat[:-len("Percentage")]
        if orig_stat in WEAPON_TYPES:
            orig_stat = "weaponKills{0}".format(orig_stat)
            return '\x02{0}\x02: {1}%'.format(stat, round( (data[orig_stat]['basic']['value'] /
                                                            data['kills']['basic']['value']) * 100, 2))
        elif orig_stat in WEAPON_CLASSES:
            return '\x02{0}\x02: {1}%'.format(stat, round( (get_weaponclass_total(data, orig_stat) /
                                                            data['kills']['basic']['value']) * 100, 2))
        else:
            return "Invalid percentage stat request {0}".format(orig_stat)
    elif stat in WEAPON_CLASSES:
        return '\x02{0}\x02: {1}'.format(stat, get_weaponclass_total(data, stat))
    elif stat == 'k/d':
        return '\x02k/d\x02: {}'.format(round(
            data['kills']['basic']['value'] / data['deaths']['basic']['value'], 2))
    elif stat == 'k/h':
        return '\x02k/h\x02: {}'.format(round(data['kills']['basic']['value'] / (
            data['secondsPlayed']['basic']['value'] / 3600), 2))
    elif stat == 'd/h':
        return '\x02d/h\x02: {}'.format(round(data['deaths']['basic']['value'] / (
            data['secondsPlayed']['basic']['value'] / 3600), 2))
    elif stat == 'avgKillDistance':
        return '\x02avgKillDistance\x02: {}m'.format(round(
            data['totalKillDistance']['basic']['value'] / data['kills']['basic']['value'], 2))
    elif stat == 'winRate':
        return '\x02winRate\x02: {}'.format(round(data['activitiesWon']['basic']['value'] / (
            data['activitiesEntered']['basic']['value'] - data['activitiesWon']['basic']['value']), 2))
    elif stat == 'precisionRate':
        return '\x02precisionRate\x02: {}'.format(round(data['precisionKills']['basic']['value'] / (
            data['kills']['basic']['value'] - data['precisionKills']['basic']['value']), 2))
    elif stat == 'bestWeapon':
        return '\x02bestWeapon\x02: {}'.format(best_weapon(data))
    else:
        return 'Invalid option {}'.format(stat)

def coo_t3(when):
    bosses = ['Thalnok, Fanatic of Crota','Balwûr','Kagoor']
    return bosses[ ((when - datetime.date(2015,9,15)).days // 7) % 3 ]

@hook.on_start()
def load_cache(bot):
    '''Load in our pickle cache and the Headers'''
    global HEADERS
    HEADERS = {'X-API-Key': bot.config.get('api_keys', {}).get('destiny', None)}
    try:
        with open('destiny_cache', 'rb') as f:
            global CACHE
            CACHE = load(f)  # and the pickles!!!
    except EOFError:
        CACHE = {}
    except FileNotFoundError:
        CACHE = {}

    CACHE.pop('collections', None)
    if not CACHE.get('links'):
        CACHE['links'] = {}
    if not CACHE.get('collections'):
        CACHE['collections'] = {'ghost_tally': 142}
    try:
        with open('lore_cache', 'rb') as f:
            global LORE_CACHE
            LORE_CACHE = load(f)  # and the pickles!!!
    except EOFError:
        LORE_CACHE = {}
    except FileNotFoundError:
        LORE_CACHE = {}

@hook.event([EventType.message, EventType.action], singlethread=True)
def discord_tracker(event, db, conn):
    if event.nick == 'DTG' and 'Command sent from Discord by' in event.content:
        global DISCORD_USER
        DISCORD_USER = event.content[event.content.find("by") + 3: -1]

def compile_stats(text, nick, bot, opts, defaults, split_defaults, st_type, notice):
    if not text:
        text = nick
    text = text.split(' ')
    CONSOLE_MAP = {"xbox": 1, "playstation": 2}

    # Do you need help?
    if text[0].lower() == 'help':
        notice('options: {}'.format(', '.join(opts + WEAPON_TYPES)))
        return

    target = compile_stats_arg_parse(text, nick)

    if target['user'] is None or not target['nick']:
        return "No possible user found."

    membership = target['user']

    # if no stats are specified, add some
    if not target['stats']:
        target['stats'] = defaults if not target['split'] else split_defaults
    split = target['split']
    path = 'characters' if split else 'mergedAllCharacters'

    output = []
    for console in membership:
        # If a console has been specified, grab only that console
        if target['console'] and console != CONSOLE_MAP[target['console']]:
            continue

        # Get stats
        try:
            data = get(
                '{}Stats/Account/{}/{}/'.format(
                    BASE_URL, console, membership[console]['membershipId']),
                headers=HEADERS
            ).json()['Response'][path]
        except KeyError:
            return 'Shit\'s broke'
        tmp_out = []
        if not split:
            try:
                data = data['results'][st_type]['allTime']
                for stat in target['stats']:
                    tmp_out.append(get_stat(data, stat))
            except KeyError:
                return "Data not available yet."
        else:
            for character in data:
                if not character['deleted'] and character['results'][st_type].get('allTime', False):
                    tmp_out.append('\x02{}\x02 {}'.format(
                        membership[console]['characters'][character['characterId']]['class'],
                        " / ".join([get_stat(character['results'][st_type]['allTime'], stat) for stat in target['stats']])
                    ))

        output.append('{}: {}'.format(CONSOLES[console - 1], ', '.join(tmp_out)))
    return '\x02{0}\x02: {1}'.format(target['nick'], '; '.join(output))

def compile_stats_arg_parse(text_arr, given_nick):
    '''Parse the input

    :param textArr: the input text array to parse
    :type  textArr: string
    :param nick: the nick to get stats on
    :type nick: string

    :returns: a dictionary of values to use
    :rtype: dictionary of strings
    '''

    CONSOLES = {"xbl": "xbox", "psn": "playstation"}
    CONSOLE2ID = {"xbox": 1, "playstation": 2}
    nick = ''
    user = None
    console = None
    collect = []
    split = False

    # Nick/console
    args = text_arr[:]
    while args:
        check_arg = args.pop(0)
        if check_arg in CONSOLES and not console:
            console = CONSOLES[check_arg]
            if user:
                # better run it again
                user = get_user(nick, CONSOLE2ID[console])
            elif collect:
                # gamertag may have been given, try it
                for i, arg in enumerate(collect):
                    user = get_user(arg, CONSOLE2ID[console])
                    if not isinstance(user, str):
                        # Gamertag given, found, remove it.
                        collect.pop(i)
                        nick = arg
                        break
        elif check_arg == 'split':
            split = True
        elif not nick:
            if console:
                # perfect, we can just return the user for it
                t = get_user(check_arg, CONSOLE2ID[console])
            else:
                # not perfect, but give it a shot
                t = get_user(check_arg)

            if not isinstance(t, str):
                # XXX: Right now, the only string returned is "A user by
                # the name (nick) can't be found." So 'string' return
                # type means that's the case; anything else is real,
                # valid, good data.
                user = t
                nick = check_arg
            else:
                # not split, not nick, not console
                # must be collect
                collect.append(check_arg)
        else:
            collect.append(check_arg)

    # If we didn't get a nick, assume the requester.
    if not nick:
        user = get_user(given_nick, CONSOLE2ID[console]) if console else get_user(given_nick)
        if not isinstance(user, str):
           nick = given_nick
        else:
           user = None

    return_dict = {'user': user, 'nick': nick, 'console': console, 'stats': collect, 'split': split}
    return return_dict


@hook.command('pvp')
def pvp(text, nick, bot, notice):
    if nick == 'DTG':
        nick = DISCORD_USER
    defaults = ['k/d', 'k/h', 'd/h', 'kills', 'bestSingleGameKills',
        'longestKillSpree', 'bestWeapon', 'secondsPlayed']
    split_defaults = ['k/d']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVP_OPTS,
        defaults=defaults,
        split_defaults=split_defaults,
        st_type='allPvP',
        notice=notice
    )

@hook.command('pve')
def pve(text, nick, bot, notice):
    if nick == 'DTG':
        nick = DISCORD_USER
    defaults = ['k/h', 'kills', 'activitiesCleared', 'longestKillSpree',
        'bestWeapon', 'secondsPlayed']
    split_defaults = ['k/d']
    return compile_stats(
        text=text,
        nick=nick,
        bot=bot,
        opts=PVE_OPTS,
        defaults=defaults,
        split_defaults=split_defaults,
        st_type='allPvE',
        notice=notice
    )

@hook.command('save')
def save_cache():
    output = 'Neither cache saved'
    with open('destiny_cache', 'wb') as f:
        dump(CACHE, f)
        output = ['Main cache saved']
    with open('lore_cache', 'wb') as f:
        dump(LORE_CACHE, f)
        output.append('Lore cache saved')
    return output


@hook.command('item')
def item_search(text, bot):
    '''
    Expects the tex to be a valid object in the Destiny database
    Returns the item's name and description.
    TODO: Implement error checking
    '''
    item = text.strip()
    itemquery = '{}Explorer/Items?name={}'.format(BASE_URL, item)
    itemHash = get(
        itemquery, headers=HEADERS).json()['Response']['data']['itemHashes']

    output = []
    for item in itemHash:
        itemquery = '{}Manifest/inventoryItem/{}'.format(BASE_URL, item)
        result = get(
            itemquery, headers=HEADERS).json()['Response']['data']['inventoryItem']

        output.append('\x02{}\x02 ({} {}{}) - \x1D{}\x1D - http://www.destinydb.com/items/{}'.format(
            result['itemName'],
            result['tierTypeName'],
            CLASS_TYPES[result['classType']],
            result['itemTypeName'],
            result.get('itemDescription', 'Item has no description.'),
            result['itemHash']
        ))
    return output[:3]

@hook.command('trials')
def trials(text,bot):
    if 'flush' in text.lower(): CACHE['trials'] = {}
    if 'last' in text.lower():
        try:
            return CACHE['last_trials']['output']
        except KeyError:
            return 'Unavailable.'
    if 'trials' in CACHE:
        if 'expiration' in CACHE['trials']:
            if datetime.datetime.utcnow() < string_to_datetime(CACHE['trials']['expiration']):
                return CACHE['trials']['output']
        if 'nextStart' in CACHE['trials']:
            if datetime.datetime.utcnow() < string_to_datetime(CACHE['trials']['nextStart']):
                time_to_trials = string_to_datetime(CACHE['trials']['nextStart']) - datetime.datetime.utcnow()
                s = time_to_trials.seconds
                h, s = divmod(s, 3600)
                m, s = divmod(s, 60)
                output = []
                if time_to_trials.days > 0:
                    output.append('{} days'.format(time_to_trials.days))
                if h: output.append('{} hours'.format(h))
                if m: output.append('{} minutes'.format(m))
                if s: output.append('{} seconds'.format(s))
                return '\x02Trials of Osiris will return in\x02 {}'.format(', '.join(output))

    advisors = get('{}advisors/V2/?definitions=true'.format(BASE_URL),headers=HEADERS).json()['Response']['data']['activities']['trials']
    if advisors['status']['active'] == False:
        CACHE['trials'] = { 'expiration': datetime_to_string(string_to_datetime(advisors['status']['startDate']) - datetime.timedelta(days=14)), 'nextStart': advisors['status']['startDate'], 'output': '\x02Trials of Osiris:\x02 Unavailable.'  }
        return trials('','')

    trials_map = get('{}Manifest/1/{}/'.format(BASE_URL,advisors['display']['activityHash']),headers=HEADERS).json()['Response']['data']['activity']['activityName']
    new_trials= { 'expiration': advisors['status']['expirationDate'], 'nextStart': datetime_to_string(string_to_datetime(advisors['status']['startDate']) + datetime.timedelta(days=7)), 'output': '\x02Trials of Osiris:\x02 {}'.format(trials_map) }

    if 'trials' in CACHE and new_trials != CACHE['trials']:
        CACHE['last_trials'] = CACHE['trials']
    CACHE['trials'] = new_trials
    return new_trials['output']

@hook.command('daily')
def daily(text,bot):
    if 'last' in text.lower():
        try:
            return CACHE['last_daily']['output']
        except KeyError:
            return 'Unavailable.'

    if 'daily' in CACHE and datetime.datetime.utcnow() < datetime.datetime.strptime(CACHE['daily']['expiration'],'%Y-%m-%dT%H:%M:%SZ'):
        return CACHE['daily']['output']

    advisors = get('{}advisors/V2/?definitions=true'.format(BASE_URL),headers=HEADERS).json()['Response']['data']
    dailycrucible = get('{}Manifest/1/{}/'.format(BASE_URL,advisors['activities']['dailycrucible']['display']['activityHash']),headers=HEADERS).json()['Response']['data']['activity']
    dailychapter = get('{}Manifest/1/{}/'.format(BASE_URL,advisors['activities']['dailychapter']['display']['activityHash']),headers=HEADERS).json()['Response']['data']['activity']
    new_daily = { 'expiration': advisors['activities']['dailycrucible']['status']['expirationDate'], 'output': '\x02Daily activities:\x02 {} || {}: {}'.format(dailycrucible['activityName'],dailychapter['activityName'],dailychapter['activityDescription']) }

    if 'daily' in CACHE and new_daily != CACHE['daily']:
        CACHE['last_daily'] = CACHE['daily']
    CACHE['daily'] = new_daily
    return new_daily['output']

@hook.command('weekly')
def weekly(text,bot):
    if 'flush' in text.lower(): CACHE['weekly'] = {}
    if 'last' in text.lower():
        try:
            return CACHE['last_weekly']['output']
        except KeyError:
            return 'Unavailable.'
    if (
        'weekly' in CACHE and
        CACHE['weekly'] != {} and
        datetime.datetime.utcnow() < datetime.datetime.strptime(CACHE['weekly']['expiration'],'%Y-%m-%dT%H:%M:%SZ')
        ):
        return CACHE['weekly']['output']

    advisors = get('{}advisors/V2/?definitions=true'.format(BASE_URL),headers=HEADERS).json()['Response']['data']

    weeklycrucible = get('{}Manifest/1/{}/'.format(
        BASE_URL,advisors['activities']['weeklycrucible']['display']['activityHash']),
        headers=HEADERS).json()['Response']['data']['activity']['activityName']

    kingsfallChallenge = []
    for activity in advisors['activities']['kingsfall']['activityTiers']:
        for skullCategory in activity['skullCategories']:
            for skull in skullCategory['skulls']:
                if 'description' in skull and skull['description'] == 'You have been challenged...':
                    if skull['displayName'] not in kingsfallChallenge: kingsfallChallenge.append(skull['displayName'])

    wotmChallenge = []
    for activity in advisors['activities']['wrathofthemachine']['activityTiers']:
        for skullCategory in activity['skullCategories']:
            for skull in skullCategory['skulls']:
                if 'description' in skull and skull['description'] == 'You have been challenged...':
                    if skull['displayName'] not in wotmChallenge: wotmChallenge.append(skull['displayName'])

    heroicstrike = []
    for skullCategory in advisors['activities']['heroicstrike']['extended']['skullCategories']:
        for skull in skullCategory['skulls']:
            heroicstrike.append(skull['displayName'])
            
    new_weekly = { 
            'expiration': advisors['activities']['weeklycrucible']['status']['expirationDate'], 
            'output': '\x02Weekly activities:\x02 {} || {} || {} || {} || Heroic Strikes: {}'.format(
                weeklycrucible, 
                ', '.join(wotmChallenge),
                ', '.join(kingsfallChallenge),
                coo_t3(datetime.date.today()), 
                ', '.join(heroicstrike)
                ) 

    if 'weekly' in CACHE and new_weekly != CACHE['weekly']:
        CACHE['last_weekly'] = CACHE['weekly']
    CACHE['weekly'] = new_weekly
    return new_weekly['output']

@hook.command('nightfall', 'nf')
def nightfall(text, bot):
    if CACHE.get('nightfall', None) and not text.lower() == 'flush':
        if 'last' in text.lower():
            return CACHE.get('last_nightfall', 'Unavailable')
        else:
            return CACHE['nightfall']
    else:
        advisors = get(
            '{}advisors/?definitions=true'.format(BASE_URL),
            headers=HEADERS).json()#['Response']['data']['nightfall']
        nightfallId = advisors['Response']['data']['nightfall']['specificActivityHash']
        nightfallActivityBundleHashId = advisors['Response']['data']['nightfall']['activityBundleHash']


        nightfallDefinition = advisors['Response']['definitions']['activities'][str(nightfallId)]

        output = '\x02{}\x02 - \x1D{}\x1D \x02Modifiers:\x02 {}'.format(
            nightfallDefinition['activityName'],
            nightfallDefinition['activityDescription'],
            ', '.join([advisors['Response']['definitions']['activities'][str(nightfallActivityBundleHashId)]['skulls'][skullId]['displayName'] for skullId in advisors['Response']['data']['nightfall']['tiers'][0]['skullIndexes']])
        )
        if 'nightfall' in CACHE and output != CACHE['nightfall']:
            CACHE['last_nightfall'] = CACHE['nightfall']
        CACHE['nightfall'] = output
        return output

@hook.command('coe')
def coe(text,bot):
    if CACHE.get('coe', None) and text.lower() not in ['flush', 'clear', 'purge']:
        if 'last' in text.lower():
            return CACHE.get('last_coe', 'Unavailable')
        else:
            return CACHE['coe']
    else:
        advisor = get('{}advisors/V2/?definitions=true'.format(BASE_URL),headers=HEADERS).json()['Response']['data']['activities']['elderchallenge']
        modifiers = []
        for skullCategory in advisor['extended']['skullCategories']:
            for skull in skullCategory['skulls']:
                modifiers.append(skull['displayName'])
        output = '\x02Challenge of the Elders\x02 - \x02Rounds:\x02 {} || \x02Modifiers:\x02 {}'.format(
            ' // '.join(BOSS_COMBATANT_HASH[round['bossCombatantHash']] for round in advisor['activityTiers'][0]['extended']['rounds']),
            ' // '.join(modifiers)
            )
        if 'coe' in CACHE and output != CACHE['coe']:
            CACHE['last_coe'] = CACHE['coe']
        CACHE['coe'] = output
        return output

@hook.command('xur')
def xur(text, bot):
    if 'last' in text.lower():
        return CACHE.get('last_xur', 'Unavailable')

    # reset happens at 9am UTC, so subtract that to simplify the math
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=9)

    # xur is available from friday's reset until sunday's reset, i.e. friday (4) and saturday (5)
    if now.weekday() not in [4, 5]:
        xursday_diff = 4 - now.weekday()
        if xursday_diff < -1: # if past saturday, bump to next week
            xursday_diff += 7

        xursday = (now + datetime.timedelta(days=xursday_diff)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_to_xursday = xursday - now

        s = time_to_xursday.seconds
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)

        output = []

        if time_to_xursday.days > 0:
            output.append('{} days'.format(time_to_xursday.days))

        if h: output.append('{} hours'.format(h))
        if m: output.append('{} minutes'.format(m))
        if s: output.append('{} seconds'.format(s))

        return '\x02Xûr will return in\x02 {}'.format(', '.join(output))

    if CACHE.get('xur', None) and not text.lower() == 'flush':
        return CACHE['xur']

    xurStock = get(
        '{}Advisors/Xur/?definitions=true'.format(BASE_URL),
        headers=HEADERS).json()['Response']

    items = [i['item'] for i in xurStock['data']['saleItemCategories'][2]['saleItems']]
    definitions = xurStock['definitions']['items']

    output = []
    for item in items:
        item_def = definitions[str(item['itemHash'])]
        stats = []
        for stat in item['stats']:
            if stat['statHash'] in STAT_HASHES and stat['value'] > 0:
                stats.append('{}: {}'.format(STAT_HASHES[stat['statHash']], stat['value']))
        output.append('{}{}'.format(
            item_def['itemName'] if 'Engram' not in item_def['itemName'] else item_def['itemTypeName'],
            ' ({})'.format(', '.join(stats)) if stats else ''
        ))
    output = ', '.join(output)

    if output != CACHE.get('xur', output):
        CACHE['last_xur'] = CACHE['xur']
    CACHE['xur'] = output
    return output

@hook.command('armsday')
def armsday(text, bot):
    if 'last' in text.lower():
        return CACHE.get('last_armsday', 'Unavailable')

    # reset happens at 9am UTC, so subtract that to simplify the math
    now = datetime.datetime.utcnow() - datetime.timedelta(hours=9)
    if now.weekday() in [0,1,6]:

        armsday_diff = 2 - now.weekday()
        if armsday_diff < -1: # if past saturday, bump to next week
            armsday_diff += 7

        armsday = (now + datetime.timedelta(days=armsday_diff)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_to_armsday = armsday - now

        s = time_to_armsday.seconds
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)

        output = []

        if time_to_armsday.days > 0:
            output.append('{} days'.format(time_to_armsday.days))

        if h: output.append('{} hours'.format(h))
        if m: output.append('{} minutes'.format(m))
        if s: output.append('{} seconds'.format(s))

        return '\x02Armsday will return in\x02 {}'.format(', '.join(output))

    if CACHE.get('armsday', None) and text.lower() not in ['flush', 'clear', 'purge']:
        return CACHE['armsday']

    advisor = get('{}advisors/V2/?definitions=true'.format(BASE_URL),
        headers=HEADERS).json()['Response']['data']['activities']['armsday']
    armsday_orders = []
    for order in advisor['extended']['orders']:
        armsday_orders.append(order['item']['itemHash'])
    for order in armsday_orders:
        armsday_orders[armsday_orders.index(order)] = get('{}Manifest/inventoryItem/{}'.format(
            BASE_URL, order),headers=HEADERS).json()['Response']['data']['inventoryItem']['itemName']
    output = '\x02Armsday orders available:\x02 {}'.format(', '.join(armsday_orders))

    if output != CACHE.get('armsday', output):
        CACHE['last_armsday'] = CACHE['armsday']
    CACHE['armsday'] = output
    return output


@hook.command('lore')
def lore(text, bot, notice):
    if not LORE_CACHE or text.lower() == 'flush':  # if the cache doesn't exist, create it
        prepare_lore_cache()
        text = ''
    complete = False
    if 'complete' in text:
        complete = True
        text = text.replace('complete', '').strip()

    name = ''
    if not text:  # if we aren't searching, return a random card
        name = sample(list(LORE_CACHE), 1)[0]
        while name == 'grim_tally':
            name = sample(list(LORE_CACHE), 1)[0]
    else:
        matches = []
        for entry in LORE_CACHE:
            if entry == 'grim_tally':
                continue
            if text.lower() == entry.lower():
                name = entry
            elif text.lower() in entry.lower() or text.lower() in LORE_CACHE[entry].get('cardDescription', '').lower():
                matches.append(entry)
        if not name:
            if len(matches) == 1:
                name = matches[0]
            elif len(matches) == 0:
                return 'I ain\'t found shit!'
            elif complete:
                notice('I found {} matches. You can choose from:'.format(len(matches)))
                for line in matches:
                    notice(line)
                return
            else:
                return ('I found {} matches, please be more specific '
                        '(e.g. {}). For a complete list use \'complete\''.format(
                            len(matches), ', '.join(matches[:3])))

    contents = LORE_CACHE[name]  # get the actual card contents
    output = strip_tags('{}: {} - {}'.format(
        name, contents.get('cardIntro', ''), contents.get('cardDescription', '')))

    if complete:
        notice(output)
        return
    elif len(output) > 300:
        output = '{}... Read more at http://www.destinydb.com/grimoire/{}'.format(
            output[:301], contents['cardId'])

    return output if len(output) > 5 else lore('', bot, notice)

@hook.command('collection')
def collection(text, nick, bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    if text:
        if text.split(' ').pop().lower() in ['xb1','xb','xbl','xbox']:
            membership = get_user(' '.join(text.split(' ')[0:len(text.split(' '))-1]),1)
            links = { 1: membership[1]['displayName']}
        elif text.split(' ').pop().lower() in ['psn','ps','playstation','ps4']:
            membership = get_user(' '.join(text.split(' ')[0:len(text.split(' '))-1]),2)
            links = { 2: membership[2]['displayName']}
        else:
            membership = get_user(text)
            if type(membership) == str:
                return 'A user by the name of {} was not found. Try specifying platform: psn or xbl'.format(text)
            links = CACHE['links'].get(text)
    else:
        membership = get_user(nick)
        links = CACHE['links'].get(nick)

    if type(membership) == str: return membership

    output = []

    for console in membership:
        grimoire = get(
            '{}Vanguard/Grimoire/{}/{}/'
            .format(BASE_URL, console, membership[console]['membershipId']),
            headers=HEADERS
        ).json()['Response']['data']
        found_frags = []
        found_siva = []
        ghosts = 0
        for card in grimoire['cardCollection']:
            if 'fragments' not in CACHE['collections']:
                # XXX: don't allow !collections to be broken
                # because of bad cache
                prepare_lore_cache()
            if card['cardId'] in CACHE['collections']['fragments']:
                found_frags.append([card['cardId']])
            elif card['cardId'] == 103094:
                ghosts = card['statisticCollection'][0]['displayValue']
            if card['cardId'] in CACHE['collections']['siva']:
               found_siva.append([card['cardId']])

        if console == 1:
            platform = "xbl"
        else:
            platform = "psn"

        output.append('{}: Grimoire {}/{}, Ghosts {}/{}, Fragments {}/{}, SIVA {}/{} - {}'.format(
            CONSOLES[console - 1],
            grimoire['score'],
            CACHE['collections']['grim_tally'],
            ghosts,
            CACHE['collections']['ghost_tally'],
            len(found_frags),
            len(CACHE['collections']['fragments']),
            len(found_siva) -1,
            len(CACHE['collections']['siva']) -1, #There are 31 cards, but only 30 associated with Cluster Pick-ups.
            try_shorten('http://destinystatus.com/{}/{}/grimoire'.format(
                platform,
                links[console]
            ))
        ))
    return output

@hook.command('link')
def link(text, nick, bot, notice):
    if nick == 'DTG':
        nick = DISCORD_USER
    text = text.lower().split(' ')
    err_msg = 'Invalid use of link command. Use: !link <gamertag> <xbl/psn>'

    # Check for right number of args
    if not 0 < len(text) < 3 or text[0] == '':
        notice(err_msg)
        return

    # Check that single arg is correct
    if len(text) == 1 and text[0] not in 'flush':
        notice(err_msg)
        return

    # Remove any previous cached char info
    CACHE[nick] = {}

    # If nick doesn't exist in cache, or we flush, reset cache value
    if not CACHE['links'].get(nick, None) or 'flush' in text:
        CACHE['links'][nick] = {}

    # Only give flush message if we flush
    if 'flush' in text:
        return '{} flushed from my cache'.format(nick)

    platform = text[1]
    gamertag = text[0]

    if platform not in ['psn', 'xbl']: # Check for a valid console
        notice(err_msg)
        return
    elif platform == 'psn':
        CACHE['links'][nick][2] = gamertag
        return '{} linked to {} on Playstation'.format(gamertag, nick)
    elif platform == 'xbl':
        CACHE['links'][nick][1] = gamertag
        return '{} linked to {} on Xbox'.format(gamertag, nick)
    else:
        notice(err_msg)
        return

@hook.command('migrate')
def migrate(text, nick, bot):
    if nick in ['weylin', 'avcables', 'DoctorRaptorMD[XB1]', 'tuzonghua']:
        global CACHE
        CACHE = {'links': CACHE['links']}
        return 'Sucessfully migrated! Now run the save command.'
    else:
        return 'Your light is not strong enough.'

@hook.command('purge')
def purge(text, nick, bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    membership = get_user(nick)

    if type(membership) is not dict:
        return membership
    user_name = nick
    output = []
    text = '' if not text else text
    try:
        if text.lower() == 'xbl' and membership.get(1, False):
            del membership[1]
            output.append('Removed Xbox from my cache on {}.'.format(user_name))
        if text.lower() == 'psn' and membership.get(2, False):
            del membership[2]
            output.append('Removed Playstation from my cache on {}.'.format(user_name))
        if not text or not membership:
            del CACHE[user_name]
            return 'Removed {}\'s characters from my cache.'.format(nick)
        else:
            CACHE[user_name] = membership
            return output if output else 'Nothing to purge. WTF you doin?!'
    except KeyError:
        return 'Bro, do you even purge?!'

@hook.command('profile')
def profile(text, nick, bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    text = nick if not text else text
    membership = get_user(text)
    if type(membership) is not dict:
        return membership

    if membership.get(1, False):
        platform = 1
        membershipId = membership.get(1)['membershipId']
    elif membership.get(2, False):
        platform = 2
        membershipId = membership.get(2)['membershipId']
    else:
        return 'No profile!'

    bungieUserId = get(
        'http://www.bungie.net/Platform/User/GetBungieAccount/{}/{}/'.format(membershipId, platform),
        headers=HEADERS).json()['Response']['bungieNetUser']['membershipId']

    return 'https://www.bungie.net/en/Profile/254/{}'.format(bungieUserId)

@hook.command('chars')
def chars(text, nick, bot, notice):
    if nick == 'DTG':
        nick = DISCORD_USER
    text = nick if not text else text
    text = text.split(' ')
    CONSOLE2ID = {"xbox": 1, "playstation": 2}

    err_msg = 'Invalid use of chars command. Use: !chars <nick> or !chars <gamertag> <psn/xbl>'

    target = compile_stats_arg_parse(text, nick)
    if target['stats'] or target['split']:
        return err_msg

    characterHash = target['user']

    if type(characterHash) is not dict:
        return 'A user by the name {} was not found.'.format(text[0])

    output = []
    for console in characterHash:
        if target['console'] and CONSOLE2ID[target['console']] != console:
            print("{0} is not {1}".format(console, target['console']))
            continue
        console_output = []
        for char in characterHash[console]['characters']:
            console_output.append('✦{} // {} // {} - {}'.format(
                characterHash[console]['characters'][char]['LL'],
                characterHash[console]['characters'][char]['class'],
                characterHash[console]['characters'][char]['race'],
                try_shorten('https://www.bungie.net/en/Legend/Gear/{}/{}/{}'.format(
                    console,
                    characterHash[console]['membershipId'],
                    char
                ))
            ))
        output.append('{}: {}'.format(
            CONSOLES[console - 1],
            ' || '.join(console_output)
        ))
    return "\x02{0}\x02: {1}".format(target['nick'], ' ; '.join(output))

@hook.command('triumphs')
def triumphs(text,nick,bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    Y2_MOT_HASH = {
        '1872531696':'Challenge of the Elders',
        '1872531697':'The Play\'s the Thing',
        '1872531698':'The Third Element',
        '1872531699':'This is Amazing',
        '1872531700':'Eris Morn\'s Revenge',
        '1872531701':'A Blade Reborn',
        '1872531702':'Return to the Reef',
        '1872531703':'The Sword Logic'
        }
    output = []
    if text:
        platform = text.split(' ').pop().lower()
        if platform not in ['psn','ps','playstation','ps4','xb1','xb','xbl','xbox']:
            return 'When using gamertag you must also supply platform'
        if platform in ['psn','ps','playstation','ps4']: platform = 2
        if platform in ['xb1','xb','xbl','xbox']: platform = 1
        membership = get_user(' '.join(text.split(' ')[0:len(text.split(' '))-1]),platform)
    else:
        membership = get_user(nick)
    if type(membership) == str: return membership
    for platform in [1,2]:
        if platform in membership:
            missing = []
            output.append(CONSOLES[platform - 1] + ':')
            book = get('{}{}/Account/{}/Advisors/?definitions=true'.format(
                BASE_URL,platform,membership[platform]['membershipId']),
                headers=HEADERS).json()['Response']['data']['recordBooks']['2175864601']
            for hash in Y2_MOT_HASH:
                if book['records'][hash]['objectives'][0]['isComplete'] == False:
                    missing.append(Y2_MOT_HASH[hash])
            if not missing: missing = ['Year Two Moments of Triumph complete!']
            output.append(', '.join(missing))
    return ' '.join(output)


@hook.command('wasted')
def wasted(text,nick,bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    if text:
        if text.split(' ').pop().lower() in ['xb1','xb','xbl','xbox']:
            membership = get_user(
                ' '.join(text.split(' ')[0:len(text.split(' '))-1]),1)
        elif text.split(
            ' ').pop().lower() in ['psn','ps','playstation','ps4']:
            membership = get_user(
                ' '.join(text.split(' ')[0:len(text.split(' '))-1]),2)
        else:
            membership = get_user(text)
            if type(membership) == str:
                return 'A user by the name of {} was not found. \
                Try specifying platform: psn or xbl'.format(text)
    else:
        membership = get_user(nick)

    if type(membership) == str:
        return membership

    for platform in zip([1,2], ['xbox', 'playstation']):

        if platform[0] in membership:
            displayname = membership[platform[0]]['displayName']

            output = []
            blue = '\x02\x0312'
            red = '\x02\x034'
            end = '\x02\x03'
            """ I'm setting these colors so that the output append is easier
            to read. Also would like to expand defaults globally in the script
            to make output easier to read and format. I'm not sure my names are
            correct for the actual color being displayed though. """

            waste = get(
                'https://www.wastedondestiny.com/api/?console={}&user={}'.format(
                    platform[0], displayname))
            data = waste.json()  # Convert our get to json formatted data.

            if data['Response'][platform[1]]:
                timePlayed = (data['Response'][platform[1]].get('timePlayed', 0))
                totalTimePlayed = str(datetime.timedelta(seconds=timePlayed))

                timeWasted = (data['Response'][platform[1]].get('timeWasted', 0))
                totalTimeWasted = str(datetime.timedelta(seconds=timeWasted))

                output.append('{}Total:{} {} || {}Wasted:{} {}'.format(blue, end,
                    totalTimePlayed, red, end, totalTimeWasted))

                return output


@hook.command('lastpvp')
def lastpvp(text,nick,bot):
    if nick == 'DTG':
        nick = DISCORD_USER
    if text:
        if text.split(' ').pop().lower() in ['xb1','xb','xbl','xbox']:
            membership = get_user(' '.join(text.split(' ')[0:len(text.split(' '))-1]),1)
        elif text.split(' ').pop().lower() in ['psn','ps','playstation','ps4']:
            membership = get_user(' '.join(text.split(' ')[0:len(text.split(' '))-1]),2)
        else:
            membership = get_user(text)
            if type(membership) == str:
                return 'A user by the name of {} was not found. Try specifying platform: psn or xbl'.format(text)
    else:
        membership = get_user(nick)

    if type(membership) == str: return membership

    output = []

    for platform in [1,2]:
        if platform in membership:
            activity = {}
            for character in membership[platform]['characters']:
                try:
                    x = get('{}Stats/ActivityHistory/{}/{}/{}/?mode=5'.format(
                        BASE_URL, platform, membership[platform]['membershipId'], character),
                        headers=HEADERS).json()['Response']['data']['activities'][0]
                    if activity == {}: activity = x; char = character
                    if 'period' in activity and x['period'] > activity['period']: activity = x; char = character
                except:
                    pass
            output.append( '(' + CONSOLES[platform-1] + ')')
            if activity['values']['standing']['basic']['displayValue'] in ['Victory','1','2','3']:
                output.append(
                    '\x02\x033\u2713 ' +
                    get('{}Manifest/2/{}/'.format(
                        BASE_URL, activity['activityDetails']['activityTypeHashOverride']),
                        headers=HEADERS).json()['Response']['data']['activityType']['activityTypeName']  +
                    '\x03\x02:')
            else:
                output.append(
                    '\x02\x034\u2717 ' +
                    get('{}Manifest/2/{}/'.format(
                        BASE_URL, activity['activityDetails']['activityTypeHashOverride']),
                        headers=HEADERS).json()['Response']['data']['activityType']['activityTypeName']  +
                    '\x03\x02:')
            output.append(
                ', '.join([
                        'Score: ' + activity['values']['score']['basic']['displayValue'],
                        'Kills: ' + activity['values']['kills']['basic']['displayValue'],
                        'Deaths: ' + activity['values']['deaths']['basic']['displayValue'],
                        '(' + activity['values']['killsDeathsRatio']['basic']['displayValue'] + ')']))
            output.append( 'http://guardian.gg/en/pgcr/' + activity['activityDetails']['instanceId'])
            pgcr = get('{}/Stats/PostGameCarnageReport/{}/'.format(
                BASE_URL,activity['activityDetails']['instanceId']),headers=HEADERS).json()['Response']['data']
            for entry in pgcr['entries']:
                if entry['characterId'] == char:
                    if 'extended' in entry:
                        if 'medalsActivityCompleteDeathless' in entry['extended']['values']: output.append('#MarkoftheUnbroken')
                        if 'medalsActivityCompleteVictoryRumbleBlowout' in entry['extended']['values']: output.append('#SumofAllTears')
                        if 'medalsActivityCompleteHighestScoreWinning' in entry['extended']['values']: output.append('#BestAround')
                        if 'medalsActivityCompleteHighestScoreLosing' in entry['extended']['values']: output.append('#OntheBrightSide')
                        if 'medalsActivityCompleteVictoryBlowout' in entry['extended']['values']: output.append('#DecisiveVictory')
                        if 'medalsActivityCompleteVictoryMercy' in entry['extended']['values']: output.append('#NoMercy')
                        if 'medalsActivityCompleteVictoryEliminationPerfect' in entry['extended']['values']: output.append('#Bulletproof')
                        if 'medalsEliminationWipeSolo' in entry['extended']['values']: output.append('#WreckingBall')
                        killSpree = ''
                        if 'medalsKillSpree1' in entry['extended']['values']: killSpree = '#Merciless'
                        if 'medalsKillSpree2' in entry['extended']['values']: killSpree = '#Relentless'
                        if 'medalsKillSpree3' in entry['extended']['values']: killSpree = '#ReignOfTerror'
                        if 'medalsKillSpreeAbsurd' in entry['extended']['values']: killSpree = '#WeRanOutOfMedals'
                        if killSpree: output.append(killSpree)
                        if 'medalsKillSpreeNoDamage' in entry['extended']['values']: output.append('#Phantom')
                        killMulti = ''
                        if 'medalsKillMulti3' in entry['extended']['values']: killMulti = '#TripleDown'
                        if 'medalsKillMulti4' in entry['extended']['values']: killMulti = '#Breaker'
                        if 'medalsKillMulti5' in entry['extended']['values']: killMulti = '#Slayer'
                        if 'medalsKillMulti6' in entry['extended']['values']: killMulti = '#Reaper'
                        if 'medalsKillMulti7' in entry['extended']['values']: killMulti = '#SeventhColumn'
                        if killMulti: output.append(killMulti)
    return " ".join(output)

@hook.command('coo')
def coo(bot):
    return 'Court of Oryx Tier 3 Boss: ' + coo_t3(datetime.date.today())

@hook.command('rules')
def rules(bot):
    return 'Check \'em! https://www.reddit.com/r/DestinyTheGame/wiki/irc'

@hook.command('100')
def the100(bot):
    return 'Check out our The100.io group here: https://www.the100.io/g/1151'

@hook.command('clan')
def clan(bot):
    return 'Check out our Clan: https://www.bungie.net/en/Clan/Detail/939927'

@hook.command('news')
def news(bot):
    feed = parse('https://www.bungie.net/en/Rss/NewsByCategory?category=destiny&currentpage=1&itemsPerPage=1')
    if not feed.entries:
        return 'Feed not found.'

    return '{} - {}'.format(
        feed['entries'][0]['summary'],
        try_shorten(feed['entries'][0]['link']))
