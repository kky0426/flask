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

api_key_ = ""


@api.route('/lol/ingame/<name>')
class Ingame(Resource):
    def get(self,name):
        start = time.time()
        uid = getUid(name)

        if uid == None:
            return make_response(json.dumps({"status" : 400,"data":"summoner not found"}))

        inGame = current_match(uid)
        if not inGame:
            return make_response(json.dumps({"status":404,"data": "not playing game"}))

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
        avgStats={"status" : 0}
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
        print(avgStats)
        print(avgStats["status"])
        if avgStats["status"] == 400:
            data = {"status" : 400,"data":"summoner not found"}
        else:
            data = {"status": 200}
            data.update(avgStats["players"][0])

        res = json.dumps(data, ensure_ascii=False, indent=4)
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
            if response.status == 200:
                inGame["players"][idx]["accountId"] = res["accountId"]


async def get_encrypted_id(name,idx,queue):
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            queue.append((idx,res["id"]))

async def get_player_info(idx,encrypted_id,inGame):
    URL = "https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/"+encrypted_id+"?api_key="+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            if not res:
                inGame["players"][idx]["wins"] = 0
                inGame["players"][idx]["losses"] =0
                inGame["players"][idx]["tier"] = "UNKNOWN"
                inGame["players"][idx]["rank"] = "UNKNOWN"

            else:
                inGame["players"][idx]["wins"] = res[0]["wins"]
                inGame["players"][idx]["losses"] = res[0]["losses"]
                inGame["players"][idx]["tier"] = res[0]["tier"]
                inGame["players"][idx]["rank"] = res[0]["rank"]

async def get_gameId(accountId,idx,queue):
    #URL = 'https://kr.api.riotgames.com/lol/match/v5/matchlists/by-puuid/' + accountId + '?season=13' + '&api_key=' + api_key_
    URL = 'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/' + accountId + '/ids?start=0&count=20&api_key='+ api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            for i in range(10):
                try:
                    queue.append((res[i],accountId,idx))
                except:
                    continue

async def get_10_game_stats(gameId,accountId,idx,inGame):
    #URL = 'https://kr.api.riotgames.com/lol/match/v5/matches/' + str(gameId) + '?api_key=' + api_key_
    URL = 'https://asia.api.riotgames.com/lol/match/v5/matches/'+gameId+'?api_key='+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
    '''
    for i in range(10):
        try:
            if res['participantIdentities'][i]['player']['accountId'] == accountId:
                playerNum = i
        except:
            return
    '''
    for i in range(10):
        try:
            if res["metadata"]["participants"][i] == accountId:
                playerNum = i
                break
        except:
            return

    duration = res["info"]["gameDuration"]/(60*60)
    inGame["players"][idx]["avgStats"]["kills"] += res["info"]['participants'][playerNum]['kills']
    inGame["players"][idx]["avgStats"]["deaths"] += res["info"]['participants'][playerNum]['deaths']
    inGame["players"][idx]["avgStats"]["assists"] += res["info"]['participants'][playerNum]['assists']
    inGame["players"][idx]["avgStats"]["gold"] += res["info"]['participants'][playerNum]['goldEarned']/duration
    inGame["players"][idx]["avgStats"]["damage_dealt"] += res["info"]['participants'][playerNum]['totalDamageDealtToChampions']/duration
    inGame["players"][idx]["avgStats"]["damage_taken"] += res["info"]['participants'][playerNum]['totalDamageTaken']/duration
    inGame["players"][idx]["avgStats"]["vision"] += res["info"]['participants'][playerNum]['visionScore']/duration
    """
    exp = 0
    if 20 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['0-10']
    if 30 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['10-20']
    if 40 < duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['20-30']
    if 50 <= duration:
        exp+= res['participants'][playerNum]['timeline']['xpPerMinDeltas']['30-40']
    """
    inGame["players"][idx]["avgStats"]["exp"] += res["info"]["participants"][playerNum]["champExperience"]/duration



async def getData(inGame):

    ac_task = [asyncio.ensure_future(getPuuid(inGame["players"][i]["summonerName"],i,inGame)) for i in range(10)]
    await asyncio.gather(*ac_task)

    encrypted_list = []

    encrypted_task = [asyncio.ensure_future(get_encrypted_id(inGame["players"][i]["summonerName"],i,encrypted_list)) for i in range(10)]
    await asyncio.gather(*encrypted_task)
    print(encrypted_list,"encrypted")
    info_task = [asyncio.ensure_future(get_player_info(idx,encrypted_id,inGame)) for idx,encrypted_id in encrypted_list]
    await asyncio.gather(*info_task)

    queue = []
    id_task = [asyncio.ensure_future(get_gameId(inGame["players"][i]["puuid"],i,queue))for i in range(10)]
    await  asyncio.gather(*id_task)

    tasks = [asyncio.ensure_future(get_10_game_stats(gameId,accountId,idx,inGame)) for gameId,accountId,idx in queue]
    await asyncio.gather(*tasks)


async def getPuuid(name,idx,inGame):
    URL = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+name+"?api_key="+api_key_
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            res = await response.json()
            if response.status == 200:

                inGame["players"][idx]["puuid"] = res["puuid"]

async def getOneStats(inGame):

    ac_task = [asyncio.ensure_future(getPuuid(inGame["players"][0]["summonerName"],0,inGame))]
    await asyncio.gather(*ac_task)

    queue = []
    if "puuid" in inGame["players"][0]:
        id_task = [asyncio.ensure_future(get_gameId(inGame["players"][0]["puuid"],0,queue))]
        await  asyncio.gather(*id_task)

    if not queue:
        inGame["status"] = 400

    tasks = [asyncio.ensure_future(get_10_game_stats(gameId,accountId,idx,inGame)) for gameId,accountId,idx in queue]
    await asyncio.gather(*tasks)


if __name__=="__main__":
    model = xgboost.XGBRegressor()
    model.load_model("model.bst")
    app.run(debug=True,host='0.0.0.0')
