# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

import sys, socket, re, platform
import threading
import sharedMethods
from tkinter import *
from tkinter.scrolledtext import *

def sendMessage(event, entry):
    message = entry.get()
    entry.delete(0, END)
    
    #receiveMessage(message) #maybe necessary if we don't get msgs we've sent back from server
def processMsgRecvd(message):
    print(message)
    
def receiveMessage(display, ssock):
    def loopfunc():
        while True:
            #Get message from server here
            message = ""
            while message == "":
                message = sharedMethods.getSocketResponse(ssock)

            #Process message
            processMsgRecvd(message)

            #Display it
            display.insert(END, message + "\n")
            display.see(END)
    return loopfunc

def serverConnect(serverSock, display, entry):
    message = ""
    while (message[0:5] != "NICK " and message[0:5] != "PASS "):
        display.insert(END, "Optionally, you may enter a password: PASS <pass> \n Otherwise, please enter a nickname: NICK <nick> \n As well as a username: USER <user> <host> <server> <real>")
        display.see(END)
        

    if message[0:5] == "PASS ":
        serverSock.send((message+"\r\n").encode("ascii"))
        reply = serverSock.recv(1024).decode("ascii")
        receiveMessage(reply)

        while message[0:5] != "NICK ":
            message = input("Please enter your nickname (NICK <nick>).")
            message = message.split()
        passwordSet = True
    sendNickUser(serverSock, message)    

    doneTalking = False

    while (not doneTalking):
        message = input("Please enter a command; QUIT to exit the server.\n")

        if message[0:4] == "QUIT":
            doneTalking = True

        serverSock.send((message+"\r\n").encode("ascii"))
        reply = serverSock.recv(512).decode("ascii")
        receiveMessage(message)

    serverSock.close()
        
def main():
    root = Tk()
    display = ScrolledText(root, height=10, width=100)
    entry = Entry(root, width=100)
    display.pack(side=TOP, fill=X)
    entry.bind('<Return>', sendMessage)
    entry.pack(side=BOTTOM, fill=X)
    continueInputs = True
    while continueInputs:
        display.insert(END, "Enter the server IP (QUIT to exit):" + "\n")
        display.see(END)
        if server == "QUIT":
            exit()
        display.insert(END, "Enter the port (QUIT to exit):" + "\n")
        display.see(END)
        if port == "QUIT":
            exit()
        port = int(port)
        serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        try:
            serverSock.connect((server, port))
            display.insert(END, ("Connected to server " + server + " on port " + port + "\n"))
            display.see(END)
        except ConnectionRefusedError:
            print("Error: Unable to connect to server.")
        thread = threading.Thread(target=receiveMessage(display, serverSock), daemon=True)
        thread.start()
        serverConnect(serverSock, display, entry)
        thread.stop()
    exit()

main()