import pymysql

class Database():
    def __init__(self):
        self.db = pymysql.connect(host='localhost',
                     port=3306,
                     user='loluser',
                     passwd='1036523',
                     db='loldb',
                     charset='utf8')

        self.cursor = self.db.cursor(pymysql.cursors.DictCursor)

    def execute(self,query,args={}):
        self.cursor.execute(query,args)

    def excuteAll(self,query,args={}):
        self.cursor.execute(query,args)
        row = self.cursor.fetchall()
        return row

    def excuteOne(self,query,args={}):
        self.cursor.execute(query,args)
        row = self.cursor.fetchone()
        return row

    def commit(self):
        self.db.commit()