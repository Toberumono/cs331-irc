class IRCException(Exception):
	pass #Not kidding here

class IRCServerException(IRCException):
	def __init__(self, message="An error relating to an IRC Server occurred"):
		super().__init__(message)

class IRCChannelException(IRCException):
	def __init__(self, message="An error relating to an IRC Channel occurred"):
		super().__init__(message)

class ConditionalDict(dict):
	def __init__(self, source=dict(), constraint=lambda key, value: True):
		super().__init__(source)
		self.__constraint = constraint

	def __setitem__(self, key, value):
		if not self.__constraint(key, value):
			raise ValueError("(" + str(key) + ", " + str(value) + ") violates the constraint on the dictionary")
		super().__setitem__(key, value)

class IRCChannelDict(ConditionalDict):
	def __init__(self, source=dict(), max_channel_length=50):
		def constraint():
			if type(key) != str:
				raise IRCChannelException(str(key) + " is not a valid IRC Channel name.  Channel names must be strings")
			if len(key) > max_channel_length:
				raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must be " + str(max_channel_length) + " characters long or less")
			fc = key[0]
			if fc != '&' and fc != '#' and fc != '+' and fc != '!':
				raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must start with either '&', '#', '+', or '!'")
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
