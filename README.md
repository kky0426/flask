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
	  “gold” : 354.1,    
	  “damage_dealt” : 515.123,  
	  “damage_taken” : 121.124,  
	  “vision” : 1.23,  
	  “exp” : 15.12  
    }  
}  
	

### /lol/ingame<name> - 게임중인 플레이어들의 평균 데이터 및 승률 예측  

#### 소환사가 존재하지 않을 때  
{ “status”  : 400 , “data” : “summoner not found”}
	
#### 소환사가 게임중이 아닐 때
{ “status” : 404 , “data” : “not playing game” }

#### 조회 성공 
{ “status” : 200,  
 “gameMode” : “CLASSIC”,  
 “gameType” : “MATCHED_GMAE”,  
 “players” : [ playerDto x 10],  
 “predict” : 0~1 ( 0에 가까울수록->red_win, 1에 가까울수록->blue_win  
}  

playerDto   
{  
	“summonerName : name,  
	“fstSpellId” : id,  
	“scnSpellId” : id,  
	“championId” : id,  
	“accountId” : account_id,  
	“wins” : 총 승리 수,  
	“losses” : 총 패배 수,  
	“tier” :  PLATINUM,  
	“rank”:	IV,  
	“avgStats” : {  
		“kills” : 3.1,  
		“deaths” : 2.3,  
		“assists” : 5,6,  
		“gold” : 354.1,  
		“damage_dealt” : 515.123,  
		“damage_taken” : 121.124,  
		“vision” : 1.23,  
		“exp” : 15.12  
	}  
}

### /board
Get - 게시판 내용 조회  

Post - 게시판 글쓰기 (name,content)  

	
	
	


	
