import re
import sharedMethods

regexes = {'special' : r'[\[\]\{\}\\`_^|]'}
patterns = {
	'user' : re.compile('^[^\r\n\0 @]+$'),
	'nickname' : re.compile('([a-zA-Z]|' + regexes['special'] + ')([a-zA-Z0-9]|-|' + regexes['special'] + ')*')
}
errors = {
	402 : ('ERR_NOSUCHSERVER', 'No such server'),
	409 : ('ERR_NOORIGIN', 'No origin specified'),
	411 : ('ERR_NORECIPIENT', 'No recipient given'),
	412 : ('ERR_NOTEXTTOSEND', 'No text to send'),
	421 : ('ERR_UNKNOWNCOMMAND', 'Unknown command'),
	431 : ('ERR_NONICKNAMEGIVEN', 'No nickname given'),
	432 : ('ERR_ERRONEUSNICKNAME', 'Erroneous nickname'),
	433 : ('ERR_NICKNAMEINUSE', 'Nickname is already in use'),
	451 : ('ERR_NOTREGISTERED', 'You have not registered'),
	461 : ('ERR_NEEDMOREPARAMS', 'Not enough parameters'),
	462 : ('ERR_ALREADYREGISTRED', 'You may not reregister'),
	464 : ('ERR_PASSWDMISMATCH', 'Password incorrect')
}
disconnection_errors = [464]

class IRCException(Exception):
	def __init__(self, message="An IRC Error occurred", *args):
		super().__init__(message, *args)
		self.message = message

class IRCServerException(IRCException):
	def __init__(self, message="An error relating to an IRC Server occurred", *args):
		super().__init__(message, *args)

class IRCChannelException(IRCException):
	def __init__(self, message="An error relating to an IRC Channel occurred", *args):
		super().__init__(message, *args)

class IRCUserException(IRCException):
	def __init__(self, message="An error relating to an IRC User occurred", *args):
		super().__init__(message, *args)

class ConditionalDict(dict):
	def __init__(self, source=dict(), constraint=lambda key, value: True):
		super().__init__(source)
		self.__constraint = constraint

	def __setitem__(self, key, value):
		if not self.__constraint(self, key, value):
			raise ValueError("(" + str(key) + ", " + str(value) + ") violates the constraint on the dictionary")
		super().__setitem__(key, value)

class IRCMessage():
	def __init__(self, raw_message, server=None):
		raw_message = raw_message.strip()
		self.server, self.params, self.source, self.command = server, [], None, None
		if len(raw_message) == 0:
			return
		self.__has_last_comm = False
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
			self.__has_last_comm = True
			last_comm = raw_message[raw_message.find(':') + 1:]
			raw_message = raw_message[0:raw_message.find(':')]
		args = re.finditer(r'("((?<!\\)")*"|[^ \r\n]+)', raw_message)
		self.params = [par.group(0) for par in args]
		if last_comm != None: self.params.append(last_comm)
		while len(self.params) > 15: #Merge the trailing arguments into a single argument
			self.params[len(self.params) - 2] = self.params[len(self.params) - 2] + " " + self.params.pop()

	def __str__(self):
		output = ""
		if self.source != None:
			output = output + ":" + self.source + " "
		output = output + self.command + " "
		if self.__has_last_comm:
			output = output + " ".join(self.params[0:len(self.params) - 1])
			output = output + " :" + str(self.params[-1])
		else:
			output = output + " ".join(self.params)
		return output + "\n"

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
			return True
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
			return True
		super().__init__(source, constraint)

class IRCTarget(dict):
	def __init__(self, sock, source=dict()):
		super().__init__(source)
		self.sock = sock
		self.name = None

	def send_message(self, message):
		self.sock.sendall(sharedMethods.encoder(str(message)))

class IRCConnection(IRCTarget):
	def __init__(self, sock, connection_type=None, source=dict()):
		super().__init__(sock=sock, source=source)
		self.connection_type = connection_type

	def isComplete(self):
		return ('PASS' in self) and ((('NICK' in self) and ('USER' in self)) or ('SERVER' in self))
