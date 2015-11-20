# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

import sys, socket, re, platform

def receiveMessage(message):
    print message

def serverConnect(server, port):
    server = int(server)
    port = int(port)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    try:
        serverSock.connect((server, port))
        print("Connected to server " + server + " on port " + port)
        
        passwordSet = False
        message = ""
        reply = "ERR_NEEDMOREPARAMS"
        passwordFail = ["ERR_NEEDMOREPARAMS", "ERR_ALREADYREGISTRED"]
        nickFail = ["ERR_NONICKNAMEGIVEN", "ERR_ERRONEUSNICKNAME", "ERR_NICKNAMEINUSE", "ERR_NICKCOLLISION", "ERR_UNAVAILRESOURCE", "ERR_RESTRICTED"]
        userFail = ["ERR_NEEDMOREPARAMS", "ERR_ALREADYREGISTRED"]
        while (reply not in userFail) and (reply not in nickFail):
            while (message[0:5] != "NICK " and message[0:5] != "PASS ") and (reply not in passwordFail)):
                message = input("Please enter either a password (PASS <pass>), or a nickname (NICK <nick>).")

            serverSock.send(message.encode("ascii"))
            reply = serverSock.recv(1024).decode("ascii")
            recieveMessage(reply)
        if message[0:5] == "PASS ":
            passwordSet = True

            while message[0:5] != "NICK ":
                message = input("Please enter your nickname (NICK <nick>).")
            serverSock.send(message.encode("ascii"))
            reply = serverSock.recv(1024).decode("ascii")
            recieveMessage(reply)

            while (message[0:5] != "USER " and (reply not in userFail)):
                message = input("Please enter your username USER <user> <mode> * <realname>.")
                reply = serverSock.recv(1024).decode("ascii")
                recieveMessage(reply
            serverSock.send(message.encode("ascii"))
            receiveMessage(serverSock.recv(1024))
            
        
        doneTalking = False
        
        while (!doneTalking):
            message = input("Please enter a command.\n")

            if message[0:4] == "QUIT":
                doneTalking = True
                
            serverSock.send(message.encode("ascii"))
            
            receiveMessage(message)
        print ("Sent message; waiting for reply")
        printout = ""
        while not printout.endswith("\r\n"):
            data = serverSock.recv(1024)
            if not len(data):
                break
            printout += data.decode("ascii")
        printout = printout[0:len(printout) - 2]

        serverSock.close()
    except ConnectionRefusedError:
        print("Error: Unable to connect to server.")
        
def main():
    continueInputs = True
    while continueInputs:
        server = input("Enter the server IP (*exit to quit):")
        if server == "*exit":
            exit()
        if server == "":
            continueInputs = False
            continue
        port = input("Enter the port (*exit to quit):")
        if port == "*exit":
            exit()
        if port == "":
            continueInputs = False
            continue

        serverConnect(server, port)