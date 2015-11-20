import sys, socket, select, re, argparse
import threading, subprocess, os.path
import helpers, sharedMethods
from server import *
from IRCShared import *

class IRCServer(Server):
	def __init__(self, port, host="", verbosity=0, listen_timeout=5, socket_timeout=1.0,
		decoder=sharedMethods.decoder, encoder=sharedMethods.encoder):
		super().__init__(port=port, host=host, verbosity=verbosity, listen_timeout=listen_timeout,
			socket_timeout=socket_timeout, decoder=decoder, encoder=encoder, server_thread=IRCServer.server_thread)
		self.channels = IRCChannelDict()
		

	def server_thread(self, clientSock, clientAddr):
		log.log("Received connection from:", str(clientAddr) + ":" + str(clientSock), level='info')

if __name__ == '__main__':
	parser = getArgumentParser()
	args = parser.parse_args()
	sharedMethods.setVerbosity(args.verbosity)
	server = IRCServer(**vars(args))
	server.start(waitForCompletion=True)
