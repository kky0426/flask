from flask import Flask,request,jsonify
from flask_restx import Api,Resource
import requests
import time
import joblib
import numpy as np

app=Flask(__name__)
api = Api(app)
api_key = "RGAPI-e10385bf-bd60-40bd-8c0c-34fb25aaf626"



@api.route('/lol/<name>')
class lol(Resource):
    def get(self,name):
        return getData(name)

@api.route('/lol/model')
class LolModel(Resource):
    def get(self):
        return
def getUid(name):
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key
    res=requests.get(URL)
    if res.status_code != 200:
        return None
    uid = res.json()["id"]
    return uid

def current(id):
    URL = "https://kr.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/"+id+"?api_key="+api_key
    res = requests.get(URL)
    if res.status_code!=200:
        return None
    people=[]
    for i in range(10):
        people.append(res.json()['participants'][i]['summonerId'])
    return people

def uidToAccount(uid):
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
    uid_list = current(uid)
    if uid_list == None:
        return {
            'status' : 404,
            'data' : 'not playing game'
        }
    account_list = []
    for uid in uid_list:
        account_list.append(uidToAccount(uid))

    player_avgStats = []
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

## accountId 로 game id 따오기 -> list return
def get_gameId(accountId):
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
    print(match_data.json()['participants'][playerNum]['timeline']['xpPerMinDeltas'])
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