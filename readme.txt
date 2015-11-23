Edward Kwiatkowski and Josh Lipstone


Commands Implemented for both the Client and Server:

PASS, NICK, USER, JOIN, PART, PRIVMSG, NOTICE, PING, PONG, QUIT
We also support displaying any errors or replies sent from the server to the client.


Files and Descriptions:

IRCclient.py - The client. Runs in the command line, asks for a server and port, then the GUI is used to exchange commands and replies with the server.
IRCServer.py - The server. Runs in the command line with a few arguments; enter to quit.
IRCShared.py - A few useful classes that are shared by the client and server.
sharedMethods.py - A few useful methods that are shared by the client and server.
server.py - The base class for the server; separated for code organization purposes.