class IRCException(Exception):
	pass #Not kidding here

class IRCServerException(IRCException):
	def __init__(self, message="An error relating to an IRC Server occurred"):
		super().__init__(message)

class IRCChannelException(IRCException):
	def __init__(self, message="An error relating to an IRC Channel occurred"):
		super().__init__(message)

class IRCChannelDict(dict):
	def __init__(self, source=dict()):
		super().__init__(source)

	def __setitem__(self, key, value):
		if type(key) != str:
			raise IRCChannelException(str(key) + " is not a valid IRC Channel name.  Channel names must be strings")
		if len(key) > 50:
			raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must be 50 characters long or less")
		fc = key[0]
		if fc != '&' and fc != '#' and fc != '+' and fc != '!':
			raise IRCChannelException(key + " is not a valid IRC Channel name.  Channel names must start with either '&', '#', '+', or '!'")
		super().__setitem__(key, value)
