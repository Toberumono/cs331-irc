import sys, socket, select, re, argparse
import threading, subprocess, os.path
import json, itertools
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
		self.channels['&test'] = IRCChannel('&test')
		self.users = IRCUserDict()
		self.locks = {'connections' : threading.RLock(), 'users' : threading.RLock(), 'channels' : threading.RLock()}
		self.connections = {'&test' : self.channels['&test']}
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

	def deregister_user(self, connection):
		with self.locks['connections']:
			if connection.name not in self.connections:
				return
			with self.locks['channels']:
				IRCServer.message_handlers['JOIN'](server, connection, IRCMessage(':' + connection.name + " JOIN 0"))
			with self.locks['users']:
				del self.users[connection.name]
			del self.connections[connection.name]
				

	def is_channel(self, name):
		with self.locks['channels']:
			return name in self.channels

	def is_nick(self, name):
		with self.locks['users']:
			return name in self.users

	def server_thread(self, clientSock, clientAddr):
		sent_ping, is_notice = False, False
		self.log("Received connection from:", str(clientAddr), level='info')
		try:
			connection = IRCConnection(sock=clientSock)
			registration_messages = 0

			while registration_messages <= 4:
				try:
					text = sharedMethods.getSocketResponse(clientSock, timeout=self.listen_timeout)
				except socket.timeout: #This handles the, "send a ping after no data goes through a connection" part
					if sent_ping: break #Then this connection is no longer live
					connection.send_message(IRCMessage("PING :" + self.host, server=self))
					sent_ping = True
					continue
				sent_ping = False
				message = IRCMessage(text, self)
				is_notice = (message.command == 'NOTICE')
				if not connection.isComplete(): registration_messages += 1 #Then we are still in the registration process
				if message.source == None: message.source = connection.name #The source of a message is, by default, the nickname of the connection

				try:
					if message.command not in IRCServer.message_handlers:
						raise IRCException(message.command, message=421)
					IRCServer.message_handlers[message.command](self, connection, message) #Then this connection is live
				except IRCException as e:
					self.log(e, level='error')
					if not is_notice and (type(e.message) == int or e.should_forward): #Then this is an error code and should be sent to the client
						self.send_error(e, connection)
						if e.message in disconnection_errors:
							break
				if message.command == 'QUIT': break
			if not connection.isComplete():
				connection.send_message(IRCMessage("ERROR"))
		except IRCException as e:
			self.log(e, level='error')
			if not is_notice and (type(e.message) == int or e.should_forward): #Then this is an error code and should be sent to the client
				self.send_error(e, connection)
		self.deregister_user(connection)
		return True

	def get_targets(self, targets):
		if type(targets) == str:
			targets = [ IRCMessageTarget(target, self) for target in targets.split(',') ]
		return [ connection for name, connection in self.connections.items() if any(helpers.ValidatorIter(name, targets)) ]

	def send_error(self, e, connection):
		reply = ":" + self.host + " " + str(e.message)
		if e.message in errors:
			reply = reply + " " + errors[e.message][0]
		connection.send_message(IRCMessage(reply, server=self))

	def send_reply(self, connection, reply, *args):
		reply = ":" + self.host + " " + reply.format(*args)
		connection.send_message(IRCMessage(reply, server=self))

class IRCChannel(IRCTarget):
	'''
	members is a list of IRCConnections
	operators is a list of IRCConnections
	bans is a list of IRCConnections
	'''
	def __init__(self, name, key=None, members=[], operators=[], bans=[], invited=[], topic="", flags=""):
		super().__init__(None, name=name)
		self.members, self.operators, self.bans, self.invited = members, operators, bans, invited
		self.flags = flags #Gonna need to parse flags
		self.key = key
		self._topic = topic

	def topic():
		doc = "The channel's topic."
		def fget(self): return self._topic
		def fset(self, value):
			with self.lock:
				'''
				Broadcast topic change here
				'''
				self._topic = value.params[1]
				self.send_message(value, None)
		def fdel(self): raise AttributeError("Cannot delete the channel's topic property.")
		return locals()
	topic = property(**topic())

	def try_join(self, key, connection):
		with self.lock:
			if 'i' in self.flags and connection not in self.invited:
				raise IRCException(self.name, message=473)
			if connection in self.bans:
				raise IRCException(self.name, message=474)
			if key != self.key:
				raise IRCException(self.name, message=475)
			self.members.append(connection)

	def try_part(self, message, connection):
		with self.lock:
			if connection not in self.members:
				raise IRCException(self.name, message=442)
			part_msg = IRCMessage("PART " + self.name + " :" + (message.params[1] if len(message.params) > 1 else connection.name), server=message.server)
			part_msg.source = connection.name
			self.send_message(part_msg, connection)
			self.members.remove(connection)
			if connection in self.operators: self.operators.remove(connection)

	def send_message(self, message, connection=None):
		with self.lock:
			if connection != None and connection not in self.members:
				raise IRCException(self.name, message=404)
			for member in self.members:
				member.send_message(message, self)

	def can_connect(self, connection, message, key=None):
		with self.lock:
			if connection.name in self.bans:
				raise IRCException(message=474)
			self.members.append(connection)

	def has_nick(self, nick):
		for member in self.members:
			if nick == member.name:
				return True
		return False

	def is_op(self, nick):
		for operator in self.operators:
			if nick == operator.name:
				return True
		return False

'''
Register message handlers here.
A message handler is a function that takes an IRCServer, an IRCConnection, and an IRCMessage and processes the message or throws an exception.
'''
def __pass(server, connection, message):
	if message.command in connection:
		raise IRCException(message=462)
	if len(message.params) < 1:
		raise IRCException(message.command, message=461)
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
		raise IRCException(message.command, message=461)
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
		raise IRCException(nick, message=432)
	with server.locks['users']:
		if server.is_nick(nick):
			raise IRCException(nick, message=433)
		connection[message.command] = nick
		oldnick = connection.name
		connection.name = nick
		if oldnick != None:
			server.connections[oldnick], server.users[oldnick] = None, None
		server.connections[connection.name], server.users[connection.name] = connection, connection
IRCServer.message_handlers['NICK'] = __nick

def __quit(server, connection, message):
	server.deregister_user(connection)
	return
IRCServer.message_handlers['QUIT'] = __quit

def __ping(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message=409)
	if len(message.params) > 1 and message.params[1] != server.host:
		if not message.params[1] in server.connections:
			raise IRCException(message.params[1], message=402)
		server.connections[message.params[1]].send_message(message, connection)
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
			raise IRCException(message.params[1], message=402)
		server.connections[message.params[1]].send_message(message, connection)
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
		raise IRCException(message.command, message=411)
	if len(message.params) < 2:
		raise IRCException(message=412)
	for tar in message.params[0].split(','):
		recipients = server.get_targets(message.params[0])
		if len(recipients) < 1:
			raise IRCException(tar, message=401)
		for recip in recipients:
			msg = IRCMessage(str(message), message.server)
			msg.params[0] = recip.name
			recip.send_message(msg, connection)
IRCServer.message_handlers['PRIVMSG'] = __privmsg
IRCServer.message_handlers['NOTICE'] = __privmsg #Notice is handled in the same way as privmsg - it just has some additional logic in the server's loop

def __join(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message.command, message=461)
	if message.params[0] == '0':
		while len(connection.channels) > 0:
			__part(server, connection, IRCMessage(':' + message.source + " PART " + connection.channels[0].name))
		return
	channels = message.params[0].split(',')
	keys = message.params[1].split(',') if len(message.params) > 1 else []
	for channel, key in itertools.zip_longest(channels, keys, fillvalue=None):
		if channel not in server.channels:
			raise IRCException(channel, message=403)
		server.channels[channel].try_join(key, connection)
		join_msg = IRCMessage("JOIN " + channel)
		join_msg.source = server.host
		connection.send_message(join_msg)
		connection.channels.append(server.channels[channel])
IRCServer.message_handlers['JOIN'] = __join

def __part(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message.command, message=461)
	channels = message.params[0].split(',')
	for channel in channels:
		if channel not in server.channels:
			raise IRCException(channel, message=403)
		server.channels[channel].try_part(message, connection)
		connection.channels.remove(server.channels[channel])
IRCServer.message_handlers['PART'] = __part

def __topic(server, connection, message):
	if not connection.isComplete():
		raise IRCException(message=451)
	if len(message.params) < 1:
		raise IRCException(message.command, message=461)
	with server.locks['channels']:
		if message.params[0] not in server.channels:
			raise IRCException(*message.params, message=442)
		channel = server.channels[message.params[0]]
		with channel.lock:
			if not channel.has_nick(message.source):
				raise IRCException(*message.params, message=442)
			if len(message.params) > 1:
				if not channel.is_op(message.source):
					raise IRCException(*message.params, message=482)
				channel.topic = message #Magic of properties
			elif channel.topic == None:
				server.send_reply(connection, replies[331], message.params[0])
			else:
				server.send_reply(connection, replies[332], message.params[0], channel.topic)
IRCServer.message_handlers['TOPIC'] = __topic

if __name__ == '__main__':
	parser = getArgumentParser()
	args = parser.parse_args()
	sharedMethods.setVerbosity(args.verbosity)
	server = IRCServer(**vars(args))
	server.start(waitForCompletion=True)
