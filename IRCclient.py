# IRC Client
# 331 Final Project
# Edward Kwiatkowski and Josh Lipstone

def serverConnect(server, port):
    port = int(port)
    serverSock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    try:
        serverSock.connect((server, port))
        print("Connected to server " + server + " on port " + port)
        
        message = input("Please enter a command: either a password (PASS <pass>), or a nickname (NICK <nick>).")
        
        passwordSet = False
        
        if message[0:5] == "PASS ":
            passwordSet = True
        
        doneTalking = False
        
        while (!doneTalking):
            message = input("Please enter a command.\n")
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
        
def main():
    