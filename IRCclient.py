# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

import sys, socket, re, platform

channel = ""



def receiveMessage(message):
    if message.split()
    if channel != "":
        message = channel + ":" + message
    
def displayCommands():
    print("the command")

def sendNickUser(sock, message):
    sock.send(message.encode("ascii"))
    reply = sock.recv(1024).decode("ascii")
    recieveMessage(reply)

    while (message[0:5] != "USER " and (reply not in userFail)):
        message = input("Please enter your username USER <user> <mode> * <realname>.")
        reply = serverSock.recv(1024).decode("ascii")
        recieveMessage(reply)
    serverSock.send(message.encode("ascii"))
    receiveMessage(serverSock.recv(1024))

def serverConnect(server, port):
    server = int(server)
    port = int(port)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    try:
        serverSock.connect((server, port))
        print("Connected to server " + server + " on port " + port)
        
        passwordSet = False
        message = ""
        while (message[0:5] != "NICK " and message[0:5] != "PASS "):
            message = input("Please enter either a password (PASS <pass>), or a nickname (NICK <nick>).")

        if message[0:5] == "PASS ":
            serverSock.send((message+"\r\n").encode("ascii"))
            reply = serverSock.recv(1024).decode("ascii")
            recieveMessage(reply)
            
            while message[0:5] != "NICK ":
                message = input("Please enter your nickname (NICK <nick>).")
            passwordSet = True
        sendNickUser(serverSock, message)    
        
        doneTalking = False
        
        while (not doneTalking):
            message = input("Please enter a command, or HELP to see a list of commands.\n")

            if message[0:4] == "QUIT":
                doneTalking = True
            if message[0:4] == "HELP":
                displayCommands()
                
            serverSock.send(message.encode("ascii"))
            receiveMessage(message)

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
    exit()

main()