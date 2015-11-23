# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

import sys, socket, re, platform, time
import threading
import sharedMethods
from IRCShared import *
from tkinter import *
from tkinter.scrolledtext import *
    
root = Tk()
display = ScrolledText(root, height=10, width=100)
def processMsgRecvd(message, ssock, nickname):
    # message : source, command, params
    parsedMessage = IRCMessage(message)
    intCommand = 0
    try:
        parsedMessage.command = int(parsedMessage.command)
        intCommand = 1
    except ValueError:
        pass
    if isinstance(parsedMessage.command, str):
        if parsedMessage.command == "PING":
            #print("pingd")
            msg = IRCMessage("PONG " + nickname + " " + str(parsedMessage.source))
            ssock.sendall(msg.encode("ascii"))
        else:
            if parsedMessage.command == "PRIVMSG" or parsedMessage.command == "NOTICE":
                dispMessage = '[' + "From: " + parsedMessage.source + ' To: ' + parsedMessage.params[0] + ']:' + (' ' + ' '.join(parsedMessage.params[1:]) if len(parsedMessage.params) > 1 else '')
            elif parsedMessage.command == "JOIN":
                dispMessage = '<' + parsedMessage.source + '>: You have joined the channel ' + parsedMessage.params[0]
            elif parsedMessage.command == "PART":
                dispMessage = '<' + parsedMessage.source + '>: You have left the channel ' + parsedMessage.params[0]
            elif parsedMessage.command == "ERROR":
                display.insert(END, "ERROR: You have been disconnected from " + parsedMessage.source + ". Closing in 10s.\n")
                time.sleep(10)
                exit()
            display.insert(END, dispMessage+"\n")
            display.see(END)
    else:
        dispMessage = "<" + parsedMessage.source + ">"
        if intCommand and (int(parsedMessage.command) >= 401 and int(parsedMessage.command) <= 599):
            dispMessage += " ERROR: "
        dispMessage += ' '.join(parsedMessage.params)
        display.insert(END, dispMessage+"\n")
        display.see(END)
    
def receiveMessage(display, ssock, nickname):
    def loopfunc():
        while True:
            #Get message from server here
            message = ""
            while message == "":
                message = sharedMethods.getSocketResponse(ssock, timeout=-1)
                
            #Process message
            processMsgRecvd(message, ssock, nickname)
    return loopfunc
        
def main():
    entry = Entry(root, width=100)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    doneTalking = False
    nickname = ""
    def sendMessage(event):
        message = entry.get()
        if (message.split(' ')[0] == "NICK") and len(message.split(' ')) >= 1:
            nickname = message.split()[1]
        if (message.strip() == "QUIT"):
            doneTalking = True
        serverSock.sendall((message+"\r\n").encode("ascii"))
        entry.delete(0, END)
    display.pack(side=TOP, fill=X)
    entry.bind('<Return>', sendMessage)
    entry.pack(side=BOTTOM, fill=X)
    continueInputs = True
    while continueInputs:
        display.insert(END, ("Please do not enter any commands until you are connected to a server."))
        display.see(END)
        
        inputs = input("Enter, separated by spaces, the server IP, and then the port:")
        if inputs == "":
            continueInputs = False
            continue
        parts = inputs.strip().split()
        try:
            serverSock.connect((parts[0], int(parts[1])))
            display.insert(END, ("Connected to server " + parts[0] + " on port " + parts[1] + "\n"))
            display.see(END)
        except ConnectionRefusedError:
            print("Error: Unable to connect to server.")
        thread = threading.Thread(target=receiveMessage(display, serverSock, nickname), daemon=True)
        thread.start()
        display.insert(END, "Optionally, you may enter a password: PASS <pass>.\n")
        display.insert(END, "Otherwise, please enter a nickname: NICK <nick>.\n")
        display.insert(END, "Finally, your username and other information: USER <user> <host> <server> <real>.\n")
        display.see(END)
        root.mainloop()
        
    exit()

main()