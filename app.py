from flask import Flask,request,jsonify
from flask_restx import Api,Resource
import requests
import time
import joblib
import numpy as np
import random

app=Flask(__name__)
api = Api(app)

api_key = "RGAPI-35c111f2-3146-419a-b169-ee9b911a1dbc"




@api.route('/lol/<name>')
class lol(Resource):
    def get(self,name):
        return getData(name)

@api.route('/lol/model')
class LolModel(Resource):
    def get(self):
        return

def getUid(name):
    #api_key = api_list[random.randrange(0, 6)]
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key
    res=requests.get(URL)
    if res.status_code != 200:
        return None
    uid = res.json()["id"]

    return uid

def current_match(uid):
    #api_key = api_list[random.randrange(0, 6)]
    URL = "https://kr.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/"+uid+"?api_key="+api_key
    res = requests.get(URL)
    data = res.json()

    if res.status_code !=200:
        return None
    inGame = {"status" : 200}
    inGame["gameMode"] = "CLASSIC"
    inGame["gameType"] = "MATCHED_GAME"
    i=1
    for person in data["participants"]:
        inGame["player_{}".format(i)] = {}
        inGame["player_{}".format(i)]["summonerName"] = person["summonerName"]
        inGame["player_{}".format(i)]["fstSpellId"] = person["spell1Id"]
        inGame["player_{}".format(i)]["scnSpellId"] = person["spell2Id"]
        inGame["player_{}".format(i)]["championId"] = person["championId"]
        i+=1
    return inGame


def uidToAccount(uid):
    #api_key = api_list[random.randrange(0, 6)]
    URL ="https://kr.api.riotgames.com/tft/summoner/v1/summoners/"+uid+"?api_key="+api_key
    res = requests.get(URL)
    return res.json()['accountId']

def getData(name):
    uid = getUid(name)
    if uid==None:
        return {
            'status' : 404,
            'data' : 'summoner not found'
        }
    ingame = current_match(uid)
    if ingame == None:
        return {
            'status' : 400,
            'data' : 'not playing game'
        }

    for i in range(1, 11):
        ingame["player_{}".format(i)]["accountId"] = uidToAccount(getUid(ingame["player_{}".format(i)]["summonerName"]))

    for i in range(1, 11):
        ingame["player_{}".format(i)]["avgStats"] = get_10_game_stats(ingame["player_{}".format(i)]["accountId"])

    return ingame

    """
    for accountId in account_list:
        player_avgStats.append(get_10_game_stats(accountId))
    p10_data = {'stats': player_avgStats}
    data=[]
    for stat in p10_data['stats']:
        for k,v in stat.items():
            if k=='exp':
                continue
            data.append(v)
    arr=np.array([data])
    predict=model.predict_proba(arr)
    return [player_avgStats,predict.tolist()]
    """

## accountId 로 game id 따오기 -> list return
def get_gameId(accountId):
    #api_key = api_list[random.randrange(0,6)]
    print(api_key)
    time.sleep(0.1)
    match = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/' + accountId + '?season=13' + '&api_key=' + api_key
    match_data = requests.get(match)

    gameId_list = []
    for i in range(4):
        try:
            gameId_list.append(match_data.json()['matches'][i]['gameId'])
        except:
            continue

    return gameId_list

def get_10_game_stats(accountId):
    gameId_list = get_gameId(accountId)
    avgData = {"kills": 0, "deaths": 0, "assists": 0, "gold": 0, "damage_dealt": 0, "damage_taken": 0, "vision": 0,
               "exp": 0}

    for game in gameId_list:
        playerData = get_playerData(game, accountId)
        if playerData != None:
            avgData["kills"] += playerData["kills"]
            avgData["deaths"] += playerData["deaths"]
            avgData["assists"] += playerData["assists"]
            avgData["damage_dealt"] += playerData["damage_dealt"]
            avgData["damage_taken"] += playerData["damage_taken"]
            avgData["vision"] += playerData["vision"]
            avgData["exp"] += playerData["exp"]
            avgData["gold"] += playerData["gold"]

    if len(gameId_list) == 0:
        avgData["kills"] = 0
        avgData["deaths"] = 0
        avgData["assists"] = 0
        avgData["damage_dealt"] = 0
        avgData["damage_taken"] = 0
        avgData["vision"] = 0
        avgData["exp"] = 0
        avgData["gold"] = 0
    else:
        avgData["kills"] /= len(gameId_list)
        avgData["deaths"] /= len(gameId_list)
        avgData["assists"] /= len(gameId_list)
        avgData["damage_dealt"] /= len(gameId_list)
        avgData["damage_taken"] /= len(gameId_list)
        avgData["vision"] /= len(gameId_list)
        avgData["exp"] /= len(gameId_list)
        avgData["gold"] /= len(gameId_list)

    time.sleep(0.1)

    return avgData


## gamgId ,accountId 로 필요한 stat 따오기 ->dictionary return
def get_playerData(gameId, accountId):
    #api_key = api_list[random.randrange(0, 6)]
    time.sleep(0.1)
    match = 'https://kr.api.riotgames.com/lol/match/v4/matches/' + str(gameId) + '?api_key=' + api_key
    match_data = requests.get(match)
    for i in range(10):
        try:
            if match_data.json()['participantIdentities'][i]['player']['accountId'] == accountId:
                playerNum = i
        except:
            return
    playerData = {"kills": match_data.json()['participants'][playerNum]['stats']['kills'],
                  "deaths": match_data.json()['participants'][playerNum]['stats']['deaths'],
                  "assists": match_data.json()['participants'][playerNum]['stats']['assists'],
                  "gold": match_data.json()['participants'][playerNum]['stats']['goldEarned'],
                  "damage_dealt": match_data.json()['participants'][playerNum]['stats']['totalDamageDealtToChampions'],
                  "damage_taken": match_data.json()['participants'][playerNum]['stats']['totalDamageTaken'],
                  "vision": match_data.json()['participants'][playerNum]['stats']['visionScore'],
                  "exp": 0
                  }
    duration = match_data.json()['gameDuration'] / 60
    print(duration)

    if 20 < duration:
        playerData['exp'] += match_data.json()['participants'][playerNum]['timeline']['xpPerMinDeltas']['0-10']
    if 30 < duration:
        playerData['exp'] += match_data.json()['participants'][playerNum]['timeline']['xpPerMinDeltas']['10-20']
    if 40 < duration:
        playerData['exp'] += match_data.json()['participants'][playerNum]['timeline']['xpPerMinDeltas']['20-30']
    if 50 <= duration:
        playerData['exp'] += match_data.json()['participants'][playerNum]['timeline']['xpPerMinDeltas']['30-40']

    for key, value in playerData.items():
        if key in ['damage_dealt', 'damage_taken', 'exp', 'gold']:
            playerData[key] = round(value / duration, 2)

    return playerData

if __name__=="__main__":
    model = joblib.load('lol_predict.pkl')
    app.run(debug=False,host='0.0.0.0')