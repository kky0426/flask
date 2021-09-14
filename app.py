from flask import Flask,request
from flask_restx import Api,Resource
import requests
import time
import aiohttp
import asyncio
import numpy as np
import xgboost
import dbconnect
import json
from flask import make_response

app=Flask(__name__)
app.config["JSON_AS_ASCII"] = False
api = Api(app)

api_key_ = "RGAPI-df6e0fe8-e1d7-49ed-9f0c-b14a10fc50f1"



@api.route('/lol/ingame/<name>')
class Ingame(Resource):
    def get(self,name):
        start = time.time()
        uid = getUid(name)
        if uid == None:
            return {"status" : 400,"data":"summoner not found"}

        inGame = current_match(uid)
        if not inGame:
            return {"status":404,"data": "not playing game"}

        for idx in range(10):
            inGame["players"][idx]["avgStats"] = {}
            inGame["players"][idx]["avgStats"]["kills"] = 0
            inGame["players"][idx]["avgStats"]["deaths"] = 0
            inGame["players"][idx]["avgStats"]["assists"] = 0
            inGame["players"][idx]["avgStats"]["gold"] = 0
            inGame["players"][idx]["avgStats"]["damage_dealt"] = 0
            inGame["players"][idx]["avgStats"]["damage_taken"] = 0
            inGame["players"][idx]["avgStats"]["vision"] = 0
            inGame["players"][idx]["avgStats"]["exp"] = 0

        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(getData(inGame))
        data = []
        for idx in range(10):
            inGame["players"][idx]["avgStats"]["kills"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["kills"])
            inGame["players"][idx]["avgStats"]["deaths"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["deaths"])
            inGame["players"][idx]["avgStats"]["assists"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["assists"])
            inGame["players"][idx]["avgStats"]["gold"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["gold"])
            inGame["players"][idx]["avgStats"]["damage_dealt"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["damage_dealt"])
            inGame["players"][idx]["avgStats"]["damage_taken"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["damage_taken"])
            inGame["players"][idx]["avgStats"]["vision"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["vision"])
            inGame["players"][idx]["avgStats"]["exp"] /= 10
            data.append(inGame["players"][idx]["avgStats"]["exp"])

        data_ = []
        for idx in range(10):
            for stat in inGame["players"][idx]["avgStats"]:
                if stat == 'exp':
                    continue
                data_.append(inGame["players"][idx]["avgStats"][stat])

        arr = np.array([data_])
        predict = model.predict(arr)
        inGame["predict"] = predict.tolist()[0]
        print(predict)
        print(time.time()-start)
        res =  json.dumps(inGame,ensure_ascii=False,indent=4)
        return make_response(res)

@api.route("/lol/<name>")
class Stats(Resource):
    def get(self,name):
        avgStats={}
        avgStats["players"] = [{}]
        avgStats["players"][0]["summonerName"] = name
        avgStats["players"][0]["avgStats"] = {}
        avgStats["players"][0]["avgStats"]["kills"] = 0
        avgStats["players"][0]["avgStats"]["deaths"] = 0
        avgStats["players"][0]["avgStats"]["assists"] = 0
        avgStats["players"][0]["avgStats"]["gold"] = 0
        avgStats["players"][0]["avgStats"]["damage_dealt"] = 0
        avgStats["players"][0]["avgStats"]["damage_taken"] = 0
        avgStats["players"][0]["avgStats"]["vision"] = 0
        avgStats["players"][0]["avgStats"]["exp"] = 0

        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(getOneStats(avgStats))

        avgStats["players"][0]["avgStats"]["kills"] /= 10
        avgStats["players"][0]["avgStats"]["deaths"] /= 10
        avgStats["players"][0]["avgStats"]["assists"] /= 10
        avgStats["players"][0]["avgStats"]["gold"] /= 10
        avgStats["players"][0]["avgStats"]["damage_dealt"] /= 10
        avgStats["players"][0]["avgStats"]["damage_taken"] /= 10
        avgStats["players"][0]["avgStats"]["vision"] /= 10
        avgStats["players"][0]["avgStats"]["exp"] /= 10

        res = json.dumps(avgStats, ensure_ascii=False, indent=4)
        return make_response(res)


@api.route("/board")
class Board(Resource):
    def get(self):
        database = dbconnect.Database()
        query = '''
            SELECT id,name,content
            FROM board
            ORDER BY id DESC       
        '''
        rows = database.excuteAll(query)
        return rows

    def post(self):
        data = request.json
        name = data["name"]
        content = data["content"]
        database = dbconnect.Database()
        query = '''INSERT INTO board (name,content)
                    VALUES(%s,%s) '''

        database.execute(query,(name,content))
        database.commit()
        return "OK"


def getUid(name):
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
    inGame["players"] = [dict() for _ in range(10)]
    i=0
    for person in data["participants"]:
        #inGame["players"][i] = {}
        inGame["players"][i]["summonerName"] = person["summonerName"]
        inGame["players"][i]["fstSpellId"] = person["spell1Id"]
        inGame["players"][i]["scnSpellId"] = person["spell2Id"]
        inGame["players"][i]["championId"] = person["championId"]
        i+=1
    return inGame


async def getAccount(name,idx,inGame):
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            inGame["players"][idx]["accountId"] = res["accountId"]




async def get_gameId(accountId,idx,queue):
    URL = 'https://kr.api.riotgames.com/lol/match/v4/matchlists/by-account/' + accountId + '?season=13' + '&api_key=' + api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()

            for i in range(10):
                try:
                    queue.append((res['matches'][i]['gameId'],accountId,idx))
                except:
                    continue


async def get_10_game_stats(gameId,accountId,idx,inGame):
    URL = 'https://kr.api.riotgames.com/lol/match/v4/matches/' + str(gameId) + '?api_key=' + api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()

    for i in range(10):
        try:
            if res['participantIdentities'][i]['player']['accountId'] == accountId:
                playerNum = i
        except:
            return
    duration = res["gameDuration"]/60
    inGame["players"][idx]["avgStats"]["kills"] += res['participants'][playerNum]['stats']['kills']
    inGame["players"][idx]["avgStats"]["deaths"] += res['participants'][playerNum]['stats']['deaths']
    inGame["players"][idx]["avgStats"]["assists"] += res['participants'][playerNum]['stats']['assists']
    inGame["players"][idx]["avgStats"]["gold"] += res['participants'][playerNum]['stats']['goldEarned']/duration
    inGame["players"][idx]["avgStats"]["damage_dealt"] += res['participants'][playerNum]['stats']['totalDamageDealtToChampions']/duration
    inGame["players"][idx]["avgStats"]["damage_taken"] += res['participants'][playerNum]['stats']['totalDamageTaken']/duration
    inGame["players"][idx]["avgStats"]["vision"] += res['participants'][playerNum]['stats']['visionScore']/duration
    exp = 0
    if 20 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['0-10']
    if 30 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['10-20']
    if 40 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['20-30']
    if 50 <= duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['30-40']
    inGame["players"][idx]["avgStats"]["exp"] += exp/duration



async def getData(inGame):

    ac_task = [asyncio.ensure_future(getAccount(inGame["players"][i]["summonerName"],i,inGame)) for i in range(10)]
    await asyncio.gather(*ac_task)


    queue = []
    id_task = [asyncio.ensure_future(get_gameId(inGame["players"][i]["accountId"],i,queue))for i in range(10)]
    await  asyncio.gather(*id_task)

    tasks = [asyncio.ensure_future(get_10_game_stats(gameId,accountId,idx,inGame)) for gameId,accountId,idx in queue]
    await asyncio.gather(*tasks)


async def getOneStats(inGame):

    ac_task = [asyncio.ensure_future(getAccount(inGame["players"][0]["summonerName"],0,inGame))]
    await asyncio.gather(*ac_task)


    queue = []
    id_task = [asyncio.ensure_future(get_gameId(inGame["players"][0]["accountId"],0,queue))]
    await  asyncio.gather(*id_task)

    tasks = [asyncio.ensure_future(get_10_game_stats(gameId,accountId,idx,inGame)) for gameId,accountId,idx in queue]
    await asyncio.gather(*tasks)


if __name__=="__main__":
    model = xgboost.XGBRegressor()
    model.load_model("model.bst")
    app.run(debug=True,host='0.0.0.0')