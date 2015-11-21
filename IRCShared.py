import re

regexes = {'special' : r'[\[\]\{\}\\`_^|]'}
patterns = {
	'user' : re.compile('^[^\r\n\0 @]+$'),
	'nickname' : re.compile('([a-zA-Z]|' + regexes['special'] + ')([a-zA-Z0-9]|-|' + regexes['special'] + ')*')
}
errors = {
	402 : ('ERR_NOSUCHSERVER', 'No such server'),
	409 : ('ERR_NOORIGIN', 'No origin specified'),
	431 : ('ERR_NONICKNAMEGIVEN', 'No nickname given'),
	432 : ('ERR_ERRONEUSNICKNAME', 'Erroneous nickname'),
	433 : ('ERR_NICKNAMEINUSE', 'Nickname is already in use'),
	461 : ('ERR_NEEDMOREPARAMS', 'Not enough parameters'),
	462 : ('ERR_ALREADYREGISTRED', 'You may not reregister')
}

class IRCException(Exception):
	def __init__(self, message="An IRC Error occurred"):
		super().__init__(message)

class IRCServerException(IRCException):
	def __init__(self, message="An error relating to an IRC Server occurred"):
		super().__init__(message)

class IRCChannelException(IRCException):
	def __init__(self, message="An error relating to an IRC Channel occurred"):
		super().__init__(message)

class IRCUserException(IRCException):
	def __init__(self, message="An error relating to an IRC User occurred"):
		super().__init__(message)

class ConditionalDict(dict):
	def __init__(self, source=dict(), constraint=lambda key, value: True):
		super().__init__(source)
		self.__constraint = constraint

	def __setitem__(self, key, value):
		if not self.__constraint(key, value):
			raise ValueError("(" + str(key) + ", " + str(value) + ") violates the constraint on the dictionary")
		super().__setitem__(key, value)

class IRCMessage():
	def __init__(self, raw_message, sever=None):
		self.raw_message = raw_message
		self.server, self.params, self.source, self.command = server, None, None, None
		if raw_message[0] == ':':
			idx = raw_message.find(' ')
			if idx < 0: raise IRCException(message="Invalid command")
			self.source = raw_message[1:idx]
			raw_message = raw_message[idx + 1:]

		idx = raw_message.find(' ')
		if idx < 0: raise IRCException(message="Invalid command")
		self.command = raw_message[0:idx]
		raw_message = raw_message[idx + 1:]
		
		last_comm = None
		if raw_message.find(':') >= 0:
			last_comm = raw_message[raw_message.find(':') + 1:]
			raw_message = raw_message[0:raw_message.find(':')]

		args = re.finditer(r'("((?<!\\)")*"|[^ ]+)', raw_message)
		self.params = [par.group(0) for par in args]
		while len(self.params) > 15: #Merge the trailing arguments into a single argument
			self.params[len(self.params) - 2] = self.params[len(self.params) - 2] + " " + self.params.pop()
		if last_comm != None: self.params.append(last_comm)

class IRCChannelDict(ConditionalDict):
	def __init__(self, source=dict(), max_channel_length=50):
		def constraint(self, key, value):
			if type(key) != str:
				raise IRCChannelException(str(key) + " is not a valid IRC Channel name.  Channel names must be strings")
			if len(key) > max_channel_length:
				raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must be " + str(max_channel_length) + " characters long or less")
			fc = key[0]
			if fc != '&' and fc != '#' and fc != '+' and fc != '!':
				raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must start with either '&', '#', '+', or '!'")
			if not re.match('^[&][^\r\n ,:]{1,' + str(max_channel_length - 1) + '}$', key):
				raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names cannot contain CR, LF, ' ', ',', or ':'")
		super().__init__(source, constraint)
		self._max_channel_length = max_channel_length

	def max_channel_length():
		doc = "The channel dictionary's max_channel_length."
		def fget(self):
			return self._max_channel_length
		def fset(self, value): raise AttributeError("Cannot change the channel dictionary's max_channel_length property.")
		def fdel(self): raise AttributeError("Cannot delete the channel dictionary's max_channel_length property.")
		return locals()
	max_channel_length = property(**max_channel_length())

class IRCUserDict(ConditionalDict):
	def __init__(self, source=dict()):
		def constraint(self, key, value):
			if type(key) != str:
				raise IRCUserException(str(key) + " is not a valid IRC Username.  Usernames must be strings")
			if not patterns['user'].match(key):
				raise IRCUserException(str(key) + " is not a valid IRC Username.  Usernames cannot contain CR, LF, ' ', or '@'")
		super().__init__(source, constraint)

class IRCTarget(dict):
	def __init__(self, sock, source=dict()):
		super().__init__(source)
		self.sock = sock

	def send_message(self, message):
		self.sock.sendall(sharedMethods.encoder(message.raw_message))

class IRCConnection(IRCTarget):
	def __init__(self, sock, connection_type=None, source=dict()):
		super().__init__(sock=sock, source=source)
		self.connection_type = connection_type

	def __setitem__(self, key, value):
		if key == None:
			key = value.command
		if type(key) != str:
			raise IRCUserException(str(key) + " is not a valid user-registration command.  All commands must be strings")
		if key in self:
			raise IRCException(message=462)
		if key == 'AUTH':
			super().__setitem__(key, value.params[0])
		elif key == 'PASS':
			if len(value.params) < 1:
				raise IRCException(message=461)
			super().__setitem__(key, value.params[0])
		elif key == 'NICK':
			if len(value.params) < 1:
				raise IRCException(message=431)
			if patterns['nickname'].fullmatch(value.params[0]) == None:
				raise IRCException(message=432)
			if server.has_nickname(value.params[0]):
				raise IRCException(message=433)
			super().__setitem__(key, value.params[0])
		elif key == 'USER':
			self.connection_type = 'USER'
			if len(value.params) < 4:
				raise IRCException(message=461)
			'''
			If we have time, we'll validate the structure of the parameters here
			'''
			super().__setitem__(key, value.params[0])
			super().__setitem__('HOST', value.params[1])
			super().__setitem__('SERVER', value.params[2])
			super().__setitem__('REAL', value.params[3])
		elif key == 'SERVER':
			self.connection_type = 'SERVER'
			'''
			Interserver components were not implemented in this assignment
			'''
		else:
			raise IRCUserException("Unexpected command")

	def isComplete(self):
		return ('PASS' in self) and ((('NICK' in self) and ('USER' in self)) or ('SERVER' in self))
