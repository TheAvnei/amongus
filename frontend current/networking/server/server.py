#imports
import socket
import threading
import json
import time
import traceback
import time

#server class
class GameServer():

    #init function
    def __init__(self):

        #constant stuff
        self.HEADER = 64
        self.PORT = 5050
        self.SERVER_IP = socket.gethostbyname(socket.gethostname())
        self.ADDR = (self.SERVER_IP, self.PORT)
        self.FORMAT = 'utf-8'
        self.DISCONNECT_MESSAGE = "leave"

        #variables
        self.killed = False
        self.numConns = 0
        self.onlinePlayers = []
        self.gameStat = "free"
        self.meetingTimer = None

        #server socket obj
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(self.ADDR)
        print("[server] socket created")

    #starts start on seperate thread
    def startServer(self):
        thread = threading.Thread(target=self.start)
        thread.start()

    #starts the server
    def start(self):

        #start listening
        self.server.listen()
        print("[server] started listening")
        while not self.killed:

            #accept new connection
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handelClient, args=(conn, addr))
            thread.start()
            self.numConns += 1

    #returns a safe player data structure
    def datStruct(self):
        playerStruct = []
        for p in self.onlinePlayers:
            playerStruct.append(p["obj"])
        return {
        "players": playerStruct,
        "gameStatus": self.gameStat
        }

    #sends stuff
    def send(self, conn, msg):

        #formatting
        message = msg.encode(self.FORMAT)

        #creating length header
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b' ' * (self.HEADER - len(send_length))

        #sending header then message
        try:
            conn.send(send_length)
            conn.send(message)
        except:
            faultyConn = None
            for p in self.onlinePlayers:
                if p["conn"] == conn:
                    faultyConn = p
            print("[client error] a send failed to \"" + p["obj"]["name"] + "\". they are now removed")
            self.onlinePlayers.remove(p)

    #dispatches update to everyone
    def dispatchUpdate(self):

        #handeling voting stuff
        if self.gameStat == "voting":
            doneVoting = True
            for p in self.onlinePlayers:
                if p["obj"]["vote"] == None:
                    doneVoting = False
            if doneVoting:
                print("--results are in--")
                for p in self.onlinePlayers:
                    print( p["obj"]["name"] + " voted for " + p["obj"]["vote"] )
                self.gameStat = "results"
                self.meetingTimer = time.time()
        if self.gameStat == "results" and self.meetingTimer != None:
            if (time.time() - self.meetingTimer) > 12:
                self.gameStat = "free"
                self.meetingTimer = None
                print("ready for next meeting")

        mess = json.dumps(self.datStruct())
        for player in self.onlinePlayers:
            conn = player["conn"]
            self.send(conn, mess)

    #handels clients
    def handelClient(self, conn, addr):

        #notify
        print("[server] new connection " + str(addr))
        p = {
        "addr": addr,
        "conn": conn,
        "obj": None
        }
        self.onlinePlayers.append( p )

        #continuosly updating player
        connected = True
        while connected:

            #reciving message
            try:
                msg_length = conn.recv(self.HEADER).decode(self.FORMAT)
                if msg_length:
                    msg_length = int(msg_length)
                    msg = conn.recv(msg_length).decode(self.FORMAT)

                    #leaving server
                    if msg == self.DISCONNECT_MESSAGE:
                        connected = False
                    else:

                        #successful update
                        p["obj"] = json.loads(msg)
                        if p["obj"]["status"] != None:

                            #starting meeting
                            if p["obj"]["status"] == "startMeeting" and self.gameStat == "free":
                                self.gameStat = "voting"
                                print("meeting started by " + p["obj"]["name"])

            except:
                print("[client error] a recive failed. they are now removed")
                connected = False
                break

        #disconnect
        self.onlinePlayers.remove(p)
        print("[server] connection left")
        conn.close()
        self.numConns -= 1

#testing the object
gs = GameServer()
gs.startServer()

#timing
fps = 50
waitTime = 1 / fps
while True:
    currTime = time.time()
    gs.dispatchUpdate()
    if( waitTime - ( time.time() - currTime ) > 0):
        time.sleep(waitTime - ( time.time() - currTime ) )
