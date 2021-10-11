# flask
[롤모델] 백엔드

## API 구조 

### /lol/<name> - 소환사 최근 10게임 데이터 조회

#### 소환사가 존재하지 않을 때
{ “status” : 400, “data” : “sommoner not found” }

#### 조회 성공
{ “status” : 200 , 
  “summonerName” : name,
  “avgStats” : {
	  “kills” : 3.1,
	  “deaths” : 2.3,
	  “assists” : 5,6,
	  “gold” : 354.1
	  “damage_dealt” : 515.123,
	  “damage_taken” : 121.124,
	  “vision” : 1.23,
	  “exp” : 15.12
    }
}

