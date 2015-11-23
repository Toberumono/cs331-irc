# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

import sys, socket, re, platform
import threading
import sharedMethods
from tkinter import *
from tkinter.scrolledtext import *
    
def processMsgRecvd(message):
    #CURRENTLY A STUB, in order to get everything else working until I properly process messages from the server
    display.insert(END, message)
    display.see(END)
    
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
        
def main():
    root = Tk()
    display = ScrolledText(root, height=10, width=100)
    entry = Entry(root, width=100)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    doneTalking = False
    def sendMessage(event):
        message = entry.get()
        if (message.strip() == "QUIT"):
            doneTalking = True
        serverSock.send((message+"\r\n").encode("ascii"))
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
            display.insert(END, ("Connected to server " + server + " on port " + port + "\n"))
            display.see(END)
        except ConnectionRefusedError:
            print("Error: Unable to connect to server.")
        thread = threading.Thread(target=receiveMessage(display, serverSock), daemon=True)
        thread.start()
        display.insert(END, "Optionally, you may enter a password: PASS <pass>.")
        display.insert(END, "Otherwise, please enter a nickname: NICK <nick>.")
        display.insert(END, "Finally, your username and other information: USER <user> <host> <server> <real>")
        display.see(END)
        while not doneTalking:
            continue
        thread.stop()
    exit()

main()