import re, threading, codecs
import sharedMethods, helpers

regexes = {'special' : r'[\[\]\{\}\\`_^|]'}
patterns = {
	'key' : re.compile('[' + codecs.decode('01', 'hex').decode('ascii') + '-' + codecs.decode('0507080C0E', 'hex').decode('ascii') + '-'
		+ codecs.decode('1F21', 'hex').decode('ascii') + '-' + codecs.decode('7F', 'hex').decode('ascii') + '\\-]{1,23}'),
	'mask' : re.compile(r'.*[*?].*'),
	'nickname' : re.compile('([a-zA-Z]|' + regexes['special'] + ')([a-zA-Z0-9]|-|' + regexes['special'] + '){,8}'),
	'user' : re.compile('^[^\r\n\0 @]+$')
}
errors = {
	401 : ('ERR_NOSUCHNICK', '{0} :No such nick/channel'),
	402 : ('ERR_NOSUCHSERVER', '{0} :No such server'),
	403 : ('ERR_NOSUCHCHANNEL', '{0} :No such channel'),
	404 : ('ERR_CANNOTSENDTOCHAN', '{0} :Cannot send to channel'),
	409 : ('ERR_NOORIGIN', ':No origin specified'),
	411 : ('ERR_NORECIPIENT', ':No recipient given ({0})'),
	412 : ('ERR_NOTEXTTOSEND', ':No text to send'),
	421 : ('ERR_UNKNOWNCOMMAND', '{0} :Unknown command'),
	431 : ('ERR_NONICKNAMEGIVEN', ':No nickname given'),
	432 : ('ERR_ERRONEUSNICKNAME', '{0} :Erroneous nickname'),
	433 : ('ERR_NICKNAMEINUSE', '{0} :Nickname is already in use'),
	442 : ('ERR_NOTONCHANNEL', '{0} :You\'re not on that channel'),
	451 : ('ERR_NOTREGISTERED', ':You have not registered'),
	461 : ('ERR_NEEDMOREPARAMS', '{0} :Not enough parameters'),
	462 : ('ERR_ALREADYREGISTRED', ':Unauthorized command (already registered)'),
	464 : ('ERR_PASSWDMISMATCH', ':Password incorrect'),
	473 : ('ERR_INVITEONLYCHAN', '{0} :Cannot join channel (+i)'),
	474 : ('ERR_BANNEDFROMCHAN', '{0} :Cannot join channel (+b)'),
	475 : ('ERR_BADCHANNELKEY', '{0} :Cannot join channel (+k)'),
	482 : ('ERR_CHANOPRIVSNEEDED', '{0} :You\'re not channel operator')
}
replies = {
	  1 : ('RPL_WELCOME', 'Welcome to our IRC server.  It\'s a class project.  Please forgive us, {0}'),
	  2 : ('RPL_YOURHOST', 'Your host is {0}, running version {1}'),
	  3 : ('RPL_CREATED', 'This server was created yesterday, or the day before that.  We don\'t really know.'),
	  4 : ('RPL_MYINFO', '{0} {1} {2} {3}'),
	331 : ('RPL_NOTOPIC', '{0} :No topic is set'),
	332 : ('RPL_TOPIC', '{0} :{1}')
}
disconnection_errors = [464]

class IRCException(Exception):
	def __init__(self, *args, message="An IRC Error occurred"):
		super().__init__(message, *args)
		self.message = message
		self.should_forward = type(message) == int
		if self.should_forward and message in errors:
			self.message = str(self.message) + " " + errors[message][1].format(*args)

class IRCServerException(IRCException):
	def __init__(self, message="An error relating to an IRC Server occurred", *args):
		super().__init__(message, *args)

class IRCChannelException(IRCException):
	def __init__(self, message="An error relating to an IRC Channel occurred", *args):
		super().__init__(message, *args)

class IRCUserException(IRCException):
	def __init__(self, message="An error relating to an IRC User occurred", *args):
		super().__init__(message, *args)

'''
A validation wrapper for a SINGLE target
'''
class IRCMessageTarget(helpers.Validator):
	def __init__(self, raw_target, server):
		self.target = raw_target
		self.server = server
		validate = self.nest_validator(lambda target: False) #Basic validator
		parts = IRCMessageTarget.__extract_uhs(raw_target)
		if len(parts) > 1:
			'''
			Will need to validate host structure
			'''
			validate = self.nest_validator(lambda target: IRCMessageTarget.__validate_uhs(target, parts))
		elif raw_target[0] == '$' or (raw_target[0] == '#' and patterns['mask'].fullmatch(raw_target[1:])):
			mask = re.compile(raw_target[1:].replace('?', '.').replace('*', '.*'))
			validate = self.nest_validator(lambda target: mask.fullmatch(target))
		elif raw_target[0] == '#' or raw_target[0] == '+' or raw_target[0] == '&' or patterns['nickname'].fullmatch(raw_target):
			validate = self.nest_validator(lambda target: target == self.target)
		else:
			validate = self.nest_validator(lambda target: False)
		super().__init__(validate)

	def __str__(self):
		return self.target

	def __eq__(self, other):
		return type(other) == type(self) and other.target == self.target and other.server == self.server

	def nest_validator(self, validator):
		return lambda target: (type(target) == IRCMessageTarget and target.target == self.target) or validator(target)

	def __extract_uhs(target):
		parts = [target]
		if '@' in parts[0]:
			loc = parts[0].rfind('@', 1, len(parts[0]) - 1)
			if loc != -1: parts = [parts[0][:loc], parts[0][loc + 1:]]
		if '!' in parts[0]: #Nicknames
			loc = parts[0].find('!', 1, 9) #Nicknames have a minimum length of 1 and a maximum length of 9
			if loc != -1 and patterns['nickname'].fullmatch(parts[0][:loc]): #If this matches the nickname!user@host structure
				parts = [parts[0][:loc], parts[0][loc + 1:]] + ([parts[1]] if len(parts) > 1 else []) #nickname!user@host
			return parts
		if '%' in parts[0]: #Users
			loc = parts[0].rfind('%', 1, len(parts[0]) - 1) #Find the last % sign that is neither the first nor last character in the string
			if loc != -1: #If such a % sign exists
				parts = [parts[0][:loc], parts[0][loc + 1:]] + ([parts[1]] if len(parts) > 1 else []) #user%host@server
		return parts
	'''
	For validating user%%host@server or user%%host
	'''
	def __validate_uhs(target, test):
		if type(target) == str:
			target = IRCMessageTarget.__extract_uhs(target)
			if len(target) < 2:
				return False
		elif type(target) != list:
			return False
		'''
		Will need to validate host structure
		'''
		return len(target) == len(test) and target == test

	def from_list(targets, server):
		if type(targets) == str:
			targets = targets.split(',')
		return [ IRCMessageTarget(raw_target=target, server=server) for target in targets ]

    #message:
    #source
    #command
    #params
class IRCMessage():
	def __init__(self, raw_message, server=None):
		raw_message = raw_message.strip()
		self.server, self.params, self._source, self.command = server, [], None, None
		if len(raw_message) == 0:
			return
		self.__has_last_comm = False
		if raw_message[0] == ':':
			idx = raw_message.find(' ')
			if idx < 0: raise IRCException(message="Invalid command")
			self.source = raw_message[1:idx]
			raw_message = raw_message[idx + 1:]

		idx = raw_message.find(' ')
		if idx < 0:
			self.command = raw_message
			return
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

	def source():
		doc = "The source of the message."
		def fget(self): return self._source
		def fset(self, value):
			if isinstance(value, IRCTarget):
				self._source = value.name
			else:
				self._source = str(value)
		def fdel(self): raise AttributeError("Cannot delete the message's source property.")
		return locals()
	source = property(**source())

class ConditionalDict(dict):
	def __init__(self, source=dict(), constraint=lambda key, value: True):
		super().__init__(source)
		self.__constraint = constraint

	def __setitem__(self, key, value):
		if not self.__constraint(self, key, value):
			raise ValueError("(" + str(key) + ", " + str(value) + ") violates the constraint on the dictionary")
		super().__setitem__(key, value)

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
			if not re.match('^[&#+!][^\r\n ,:]{1,' + str(max_channel_length - 1) + '}$', key):
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
	def __init__(self, sock, name=None, source=dict()):
		super().__init__(source)
		self.sock = sock
		self.name = name
		self.lock = threading.RLock()

	def send_message(self, message, connection=None):
		if connection == None: connection = self
		with self.lock:
			self.sock.sendall(sharedMethods.encoder(str(message)))

class IRCConnection(IRCTarget):
	def __init__(self, sock, connection_type=None, source=dict()):
		super().__init__(sock=sock, source=source)
		self.connection_type = connection_type
		self.channels = []

	def isComplete(self):
		return ('PASS' in self) and ((('NICK' in self) and ('USER' in self)) or ('SERVER' in self))
