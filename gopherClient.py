'''
A simple "echo" client written in Python.

author:  Amy Csizmar Dalal and Edward Kwiatkowski and Josh Lipstone
CS 331, Fall 2015
date:  21 September 2015
'''
import sys, socket, re, platform

def escape(string):
    s = string
    i, string = 0, ""
    while i < len(s):
        if s[i] == '\\':
            i += 1
            if i >= len(s):
                print("Your string, " + s + ", was malformatted at index: " + str(i))
                return
            c = s[i]
            if c == 't':
                string += "\t"
            elif c == 'b':
                string += "\b"
            elif c == 'n':
                string += "\n"
            elif c == 'r':
                string += "\r"
            elif c == 'f':
                string += "\f"
            elif c == '\'':
                string += "\'"
            elif c == '"':
                string += "\""
            elif c == '\\':
                string += "\\"
            else:
                print("Your string, " + s + ", was malformatted at index: " + str(i))
                return
        else:
            string += s[i]
        i += 1
    return string

def serverConnect(server, port, message, inFolder):
    port = int(port)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    try:
        serverSock.connect((server, port))
        print ("Connected to server; sending message:")
        print(message)

        serverSock.send(message.encode("ascii"))
        #print ("Sent message; waiting for reply")
        printout = ""
        while not printout.endswith("\n."):
            data = serverSock.recv(1024)
            if not len(data):
                break
            printout += data.decode("ascii")
        printout = printout[0:len(printout) - 2]

        #print ("Received reply")
        folders = []
        for line in printout.split("\n"):
            pstring = ""
            if inFolder:
                name = line.split("\t")[0][1:]
                if line[0] == "0":
                    pstring += "File: "
                elif line[0] == "1":
                    pstring += "Folder: "
                    folders.append(name)
                print(pstring + name)
            else:
                print(line)
        return folders

        serverSock.close()
    except ConnectionRefusedError:
        print("Error: Unable to connect to server.")
        
def gopherBrowser(server, port):
    folders = serverConnect(server, port, "\r\n", True)
    continueFiles = True
    directoryStack = []
    while continueFiles:
        print("-----------------------------------------------------------------------------")
        print("Select a file or directory by typing its name, or:")
        print("- an empty line to see the contents of the current directory,")
        print("- '*return' to go to up one level in the filesystem,")
        print("- '*cancel' to return to server selection,")
        decision = input("- '*exit' to quit entirely. \n")
        print("-----------------------------------------------------------------------------")
        if decision == "*cancel":
            continueFiles = False
            continue
        if decision == "*exit":
            exit()
        if decision == "*return":
            decision = ""
            if len(directoryStack) == 0:
                print("You are already in the top level directory.")
            else:
                del directoryStack[len(directoryStack)-1]
        inFolder = False
        if decision == "":
            inFolder = True
        if decision in folders:
            inFolder = True
            directoryStack.append(decision)
            decision = ""
        if "/".join(directoryStack) != "":
            decision = "/" + decision
        folders = serverConnect(server, port, "/".join(directoryStack) + decision + "\r\n", inFolder)

def main():
    # Process command line args (server, port, message)
    mode = input("Please select 's'imple or 'c'ondensed input mode. (Type 's' or 'c' and hit enter.)")
    
    if mode == 's':
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
                            
            gopherBrowser(server, port)

    elif mode == 'c':
        continueInputs = True
        while continueInputs:
            inputs = input("Enter, separated by spaces, the server IP, and then the port:")
            if inputs == "":
                continueInputs = False
                continue
            
            parts = inputs.strip().split()
            
            gopherBrowser(parts[0], parts[1])
    
    else:
        print("Illegal command. Exiting now.")

main()