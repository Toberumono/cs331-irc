import sys, socket, select, re, argparse
import threading, subprocess, os.path
import helpers, sharedMethods
from server import *
from IRCShared import *

class IRCServer(Server):
	def __init__(self, port, host="", verbosity=0, listen_timeout=5, socket_timeout=1.0,
		decoder=sharedMethods.decoder, encoder=sharedMethods.encoder):
		super().__init__(port=port, host=host, verbosity=verbosity, listen_timeout=listen_timeout,
			socket_timeout=socket_timeout, decoder=decoder, encoder=encoder, socket_thread=IRCServer.server_thread,
			force_empty_host=True)
		self.channels = IRCChannelDict()
		self.users = IRCUserDict()
		self.connections = {}
		
	def has_nickname(self, nickname):
		for k, usr in self.users.items():
			if usr['NICK'] == nickname:
				return True
		return False

	def server_thread(self, clientSock, clientAddr):
		sent_ping = False
		self.log("Received connection from:", str(clientAddr) + ":" + str(clientSock), level='info')
		try:
			'''
			Authentication phase.
			'''
			connection = IRCConnection(sock=clientSock)
			registration_messages = 0
			while not connection.isComplete() and registration_messages < 4:
				message = IRCMessage(sharedMethods.getSocketResponse(clientSock), self)
				connection[message.command] = message
				registration_messages += 1
			if not connection.isComplete(): #If the 4 command-limit is exceeded.
				clientSock.sendall(sharedMethods.encoder("KILL" + (" " + connection['NICK'] if 'NICK' in connection else "")))
				return True
			if 'USER' in connection:
				self.connections[connection['USER']] = connection
				self.users[connection['USER']] = connection
			elif 'SERVER' in connection:
				self.connections[connection['SERVER']] = connection

			'''
			Connected phase
			'''
			is_notice = False
			while True:
				text = sharedMethods.getSocketResponse(clientSock)
				if text == "": #Nothing was received on this connection
					if sent_ping: #Then this connection is no longer live
						break
					clientSock.sendall("PING :" + self.host)
					sent_ping = True
					continue
				sent_ping = False
				message = IRCMessage(text, self)
				is_notice = (message.command == 'NOTICE')
				if message.command == 'QUIT':
					break
				try:
					__message_handlers[message.command](connection, message) #Then this connection is live
				except IRCException as e:
					if is_notice: #Don't send an error reply
						continue
					if type(e.message) == int: #Then this is an error code and should be sent to the client
						reply = ":" + self.host + " " + str(e.message)
						if e.message in errors:
							reply = reply + " " + errors[e.message][0]
						clientSock.sendall(reply)
		except IRCException as e:
			self.log(e, level='error')
			if type(e.message) == int: #Then this is an error code and should be sent to the client
				clientSock.sendall(sharedMethods.encoder(str(e.message)))
		except Exception as e2:
			print(e2)
		finally:
			return True

__message_handlers = {}

'''
Register message handlers here.
A message handler is a function that takes an IRCServer, an IRCConnection, and an IRCMessage and processes the message or throws an exception.
'''
def __ping(server, connection, message):
	if len(message.params) < 1:
		raise IRCException(message=409)
	if len(message.params) > 1 and message.params[1] != server.host:
		if not message.params[1] in server.connections:
			raise IRCException(message=402)
		server.connections[message.params[1]].sock.sendall(sharedMethods.encoder(message.raw_message))
		return False
	connection.sock.sendall(sharedMethods.encoder("PONG " + server.host + " " + message.params[0]))
	return True
__message_handlers['PING'] = __ping

def __pong(server, connection, message):
	if len(message.params) < 1:
		raise IRCException(message=409)
	if len(message.params) > 1 and message.params[1] != server.host:
		if not message.params[1] in server.connections:
			raise IRCException(message=402)
		server.connections[message.params[1]].sock.sendall(sharedMethods.encoder(message.raw_message))
		return False
	return True
__message_handlers['PONG'] = __pong

def __error(server, connection, message):
	'''
	ERROR handling is part of the server-server aspect of IRC and is not implemented as part of this project.
	'''
__message_handlers['ERROR'] = __error

def __privmsg(server, connection, message):
	if len(message.params) < 1:
		raise IRCException(message=411)
	if len(message.params) < 2:
		raise IRCException(message=412)
	if message.source == None:
		message.source = connection.name
	for recip in message.params[0].split(','):
		server.connections[recip].send_message(message)
__message_handlers['PRIVMSG'] = __privmsg
__message_handlers['NOTICE'] = __privmsg #Notice is handled in the same way as privmsg - it just has some additional logic in the server's loop

if __name__ == '__main__':
	parser = getArgumentParser()
	args = parser.parse_args()
	sharedMethods.setVerbosity(args.verbosity)
	server = IRCServer(**vars(args))
	server.start(waitForCompletion=True)
