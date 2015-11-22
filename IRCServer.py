import sys, socket, select, re, argparse
import threading, subprocess, os.path
import json
import helpers, sharedMethods
from server import *
from IRCShared import *

class IRCServer(Server):
	message_handlers = {}
	def __init__(self, port, host="", verbosity=0, listen_timeout=5, socket_timeout=1.0,
		decoder=sharedMethods.decoder, encoder=sharedMethods.encoder):
		super().__init__(port=port, host=host, verbosity=verbosity, listen_timeout=listen_timeout,
			socket_timeout=socket_timeout, decoder=decoder, encoder=encoder, socket_thread=IRCServer.server_thread,
			force_empty_host=True)
		self.channels = IRCChannelDict()
		self.users = IRCUserDict()
		self.locks = {'connections' : threading.RLock(), 'users' : threading.RLock()}
		self.connections = {}
		self.__login_data = json.load(open("./userpass.json")) if os.path.isfile("./userpass.json") else {}

	def register_user(self, connection):
		with self.locks['users']:
			if connection['USER'] in self.__login_data:
				if self.__login_data[connection['USER']] != connection['PASS']:
					raise IRCException(message=464)
			else:
				self.__login_data[connection['USER']] = connection['PASS']
				json.dump(self.__login_data, open("./userpass.json", 'w'))
				with self.locks['connections']:
					self.connections[connection.name] = connection
				self.users[connection.name] = connection


	def has_nickname(self, nickname):
		with self.locks['users']:
			for k, usr in self.users.items():
				if usr['NICK'] == nickname:
					return True
		return False

	def server_thread(self, clientSock, clientAddr):
		sent_ping = False
		self.log("Received connection from:", str(clientAddr), level='info')
		try:
			'''
			Authentication phase.
			'''
			connection = IRCConnection(sock=clientSock)
			registration_messages = 0

			'''
			Connected phase
			'''
			is_notice = False
			while registration_messages < 4:
				try:
					text = sharedMethods.getSocketResponse(clientSock, timeout=self.listen_timeout)
				except socket.timeout:
					if sent_ping: #Then this connection is no longer live
						break
					connection.send_message(IRCMessage("PING :" + self.host, server=self))
					sent_ping = True
					continue
				sent_ping = False
				message = IRCMessage(text, self)
				is_notice = (message.command == 'NOTICE')
				if message.command == 'QUIT':
					break
				if not connection.isComplete(): registration_messages += 1
				try:
					if message.command not in IRCServer.message_handlers:
						raise IRCException(message=421)
					IRCServer.message_handlers[message.command](self, connection, message) #Then this connection is live
				except IRCException as e:
					if is_notice: #Don't send an error reply
						continue
					if type(e.message) == int: #Then this is an error code and should be sent to the client
						self.send_error(e, connection)
						if e.message in disconnection_errors:
							break
			if not connection.isComplete():
				connection.send_message(IRCMessage("ERROR"))
		except IRCException as e:
			self.log(e, level='error')
			if type(e.message) == int: #Then this is an error code and should be sent to the client
				clientSock.sendall(sharedMethods.encoder(str(e.message)))
		return True

	def send_error(self, e, connection):
		reply = ":" + self.host + " " + str(e.message)
		if e.message in errors:
			reply = reply + " " + errors[e.message][0]
		connection.send_message(IRCMessage(reply, server=self))

'''
Register message handlers here.
A message handler is a function that takes an IRCServer, an IRCConnection, and an IRCMessage and processes the message or throws an exception.
'''
def __pass(server, connection, message):
	if message.command in connection:
		raise IRCException(message=462)
	if len(message.params) < 1:
		raise IRCException(message=461)
	connection[message.command] = message.params[0]
	if connection.isComplete():
		if 'USER' in connection:
			server.register_user(connection)
IRCServer.message_handlers['AUTH'] = __pass #We aren't handling AUTH, so this is a convenient placeholder
IRCServer.message_handlers['PASS'] = __pass

def __user(server, connection, message):
	if message.command in connection or 'SERVER' in connection:
		raise IRCException(message=462)
	connection.connection_type = 'USER'
	if len(message.params) == 1: #This is a connection from a client
		connection[message.command] = message.params[0]
	elif len(message.params) >= 4:
		'''
		If we have time, we'll validate the structure of the parameters here
		'''
		connection[message.command] = message.params[0]
		connection['HOST'] = message.params[1]
		connection['SERVER'] = message.params[2]
		connection['REAL'] = message.params[3]
	else:
		raise IRCException(message=461)
	if connection.isComplete():
		server.register_user(connection)
IRCServer.message_handlers['USER'] = __user

def __nick(server, connection, message):
	if len(message.params) < 1:
		raise IRCException(message=431)
	nick = message.params[0]
	if message.command in connection and not connection.isComplete():
			raise IRCException(message=451)
	if patterns['nickname'].fullmatch(nick) == None:
		raise IRCException(message=432)
	with server.locks['users']:
		if server.has_nickname(nick):
			raise IRCException(message=433)
		connection[message.command] = nick
		oldnick = connection.name
		connection.name = nick
		server.connections[oldnick], server.connections[connection.name] = None, connection
		server.users[oldnick], server.users[connection.name] = None, connection
IRCServer.message_handlers['NICK'] = __nick

def __ping(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message=409)
	if len(message.params) > 1 and message.params[1] != server.host:
		if not message.params[1] in server.connections:
			raise IRCException(message=402)
		server.connections[message.params[1]].send_message(message)
		return False
	connection.sock.sendall(sharedMethods.encoder("PONG " + server.host + " " + message.params[0]))
	return True
IRCServer.message_handlers['PING'] = __ping

def __pong(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message=409)
	if len(message.params) > 1 and message.params[1] != server.host:
		if not message.params[1] in server.connections:
			raise IRCException(message=402)
		server.connections[message.params[1]].send_message(message)
		return False
	return True
IRCServer.message_handlers['PONG'] = __pong

def __error(server, connection, message):
	'''
	ERROR handling is part of the server-server aspect of IRC and is not implemented as part of this project.
	'''
IRCServer.message_handlers['ERROR'] = __error

def __privmsg(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message=411)
	if len(message.params) < 2:
		raise IRCException(message=412)
	if message.source == None:
		message.source = connection.name
	for recip in message.params[0].split(','):
		server.connections[recip].send_message(message)
IRCServer.message_handlers['PRIVMSG'] = __privmsg
IRCServer.message_handlers['NOTICE'] = __privmsg #Notice is handled in the same way as privmsg - it just has some additional logic in the server's loop

if __name__ == '__main__':
	parser = getArgumentParser()
	args = parser.parse_args()
	sharedMethods.setVerbosity(args.verbosity)
	server = IRCServer(**vars(args))
	server.start(waitForCompletion=True)
