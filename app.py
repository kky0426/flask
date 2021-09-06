from flask import Flask,request,jsonify
from flask_restx import Api,Resource
import requests
import time
import pickle
import aiohttp
import asyncio
import numpy as np
import xgboost

app=Flask(__name__)
api = Api(app)

api_key_ = "RGAPI-df6e0fe8-e1d7-49ed-9f0c-b14a10fc50f1"


@api.route('/api/time')
class gettime(Resource):
    def get(self):
        start = time.time()
        URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+"학대견황구"+"?api_key="+api_key_
        for i in range(10):
            res = requests.get(URL)
        return time.time()-start

@api.route('/api_key')
class api_key(Resource):
    def get(self):
        global api_key
        return {"api_key" : api_key_}

@api.route('/lol/<name>')
class lol(Resource):
    def get(self,name):
        start = time.time()
        uid = getUid(name)
        if uid == None:
            return {"status" : 400,"data":"summoner not found"}

        inGame = current_match(uid)
        print(inGame)
        if not inGame:
            return {"status":404,"data": "not playing game"}

        for idx in range(1, 11):
            inGame["player_{}".format(idx)]["avgStats"] = {}
            inGame["player_{}".format(idx)]["avgStats"]["kills"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["deaths"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["assists"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["gold"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["damage_dealt"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["damage_taken"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["vision"] = 0
            inGame["player_{}".format(idx)]["avgStats"]["exp"] = 0

        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(getData(inGame))
        data = []
        for idx in range(1, 11):
            inGame["player_{}".format(idx)]["avgStats"]["kills"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["kills"])
            inGame["player_{}".format(idx)]["avgStats"]["deaths"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["deaths"])
            inGame["player_{}".format(idx)]["avgStats"]["assists"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["assists"])
            inGame["player_{}".format(idx)]["avgStats"]["gold"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["gold"])
            inGame["player_{}".format(idx)]["avgStats"]["damage_dealt"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["damage_dealt"])
            inGame["player_{}".format(idx)]["avgStats"]["damage_taken"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["damage_taken"])
            inGame["player_{}".format(idx)]["avgStats"]["vision"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["vision"])
            inGame["player_{}".format(idx)]["avgStats"]["exp"] /= 10
            data.append(inGame["player_{}".format(idx)]["avgStats"]["exp"])

        data_ = []
        for i in range(1, 11):
            for stat in inGame["player_{}".format(i)]["avgStats"]:
                if stat == 'exp':
                    continue
                data_.append(inGame["player_{}".format(i)]["avgStats"][stat])

        arr = np.array([data_])
        predict = model.predict(arr)
        print(predict)

        return inGame



def getUid(name):
    #api_key = api_list[random.randrange(0, 6)]
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key_
    res=requests.get(URL)
    if res.status_code != 200:
        return None
    uid = res.json()["id"]

    return uid

def current_match(uid):
    URL = "https://kr.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/"+uid+"?api_key="+api_key_
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


async def getAccount(name,idx,inGame):
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            inGame["player_{}".format(idx)]["accountId"] = res["accountId"]




async def get_gameId(accountId,idx):
    URL = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/' + accountId + '?season=13' + '&api_key=' + api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()


            gameId_list = []
            for i in range(10):
                try:
                    gameId_list.append((res['matches'][i]['gameId'],accountId,idx))
                except:
                    continue

            return gameId_list

async def get_10_game_stats(gameId,accountId,idx,inGame):
    URL = 'https://kr.api.riotgames.com/lol/match/v4/matches/' + str(gameId) + '?api_key=' + api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            print("api call")
            res = await response.json()

    for i in range(10):
        try:
            if res['participantIdentities'][i]['player']['accountId'] == accountId:
                playerNum = i
        except:
            return
    duration = res["gameDuration"]/60
    inGame["player_{}".format(idx)]["avgStats"]["kills"] += res['participants'][playerNum]['stats']['kills']
    inGame["player_{}".format(idx)]["avgStats"]["deaths"] += res['participants'][playerNum]['stats']['deaths']
    inGame["player_{}".format(idx)]["avgStats"]["assists"] += res['participants'][playerNum]['stats']['assists']
    inGame["player_{}".format(idx)]["avgStats"]["gold"] += res['participants'][playerNum]['stats']['goldEarned']/duration
    inGame["player_{}".format(idx)]["avgStats"]["damage_dealt"] += res['participants'][playerNum]['stats']['totalDamageDealtToChampions']/duration
    inGame["player_{}".format(idx)]["avgStats"]["damage_taken"] += res['participants'][playerNum]['stats']['totalDamageTaken']/duration
    inGame["player_{}".format(idx)]["avgStats"]["vision"] += res['participants'][playerNum]['stats']['visionScore']/duration
    exp = 0
    if 20 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['0-10']
    if 30 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['10-20']
    if 40 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['20-30']
    if 50 <= duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['30-40']
    inGame["player_{}".format(idx)]["avgStats"]["exp"] += exp/duration



async def getData(inGame):

    #for i in range(1,11):
    #    getAccount(inGame["player_{}".format(i)]["summonerName"],i)

    ac_task = [asyncio.ensure_future(getAccount(inGame["player_{}".format(i)]["summonerName"],i,inGame)) for i in range(1,11)]
    await asyncio.gather(*ac_task)

    queue = []
    for i in range(1,11):
        queue+= await get_gameId(inGame["player_{}".format(i)]["accountId"],i)
    tasks = [asyncio.ensure_future(get_10_game_stats(gameId,accountId,idx,inGame)) for gameId,accountId,idx in queue]
    await asyncio.gather(*tasks)





if __name__=="__main__":
    model = xgboost.XGBRegressor()
    model.load_model("model.bst")
    app.run(debug=True,host='0.0.0.0')