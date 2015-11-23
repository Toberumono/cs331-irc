import sys, socket, select, re, argparse
import threading, subprocess, os.path
import helpers, sharedMethods

class Server(helpers.ThreeStateLogger):

	def __init__(self, port, host="", verbosity=0, listen_timeout=5, socket_timeout=1.0,
		decoder=sharedMethods.decoder, encoder=sharedMethods.encoder, socket_thread=lambda server, clientSock, clientAddr: None, force_empty_host=False):
		super().__init__(verbosity)
		self._running, self.__runningLock = False, threading.RLock()
		self._port, self._host = port, host
		self._listen_timeout, self._socket_timeout = listen_timeout, socket_timeout
		self._decoder, self._encoder = decoder, encoder
		self._socket_thread = socket_thread
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind(("" if force_empty_host else self.host, self.port))

	def start(self, waitForCompletion=True):
		with self.__runningLock:
			if self.isRunning():
				return True
			self._running = True
			self.socket.listen(10)
			self.socket.settimeout(self.socket_timeout)
			serv = threading.Thread(target=self.listenThread, daemon=True)
			serv.start()
		return self.awaitCompletion() if waitForCompletion else self.isRunning()

	'''
	Returns: True if the server is running when the method terminates.
	'''
	def awaitCompletion(self):
		if not self.isRunning(): return self.isRunning()
		sys.stdout.write("Server started.  Press the Enter key to stop it.\n")
		sys.stdout.flush()
		while self.isRunning():
			ready, _, _ = select.select([sys.stdin], [],[], 1.0)
			if ready and sys.stdin.readline() != "":
				self.stop()
		return self.isRunning()

	def stop(self):
		with self.__runningLock:
			if not self.isRunning():
				return True
			self._running = False
			sharedMethods.socketCloser(self.socket)
			return not self.isRunning()

	'''
	In order to allow the server to be stopped without a keyboard interrupt,
	we have the component that listens for connections in its own function.
	This is then fed into a Thread within the listen function.  I couldn't
	come up with a better name for it, so... listenThread.
	'''
	def listenThread(self):
		while self.isRunning():
			try:
				clientSock, clientAddr = self.socket.accept()
				clientSock.settimeout(None) #Disable the socket's internal timeout system.
				#Spin off a new thread to handle this client
				cli = threading.Thread(target=Server.__serverLoop, args=(self, self.socket_thread, clientSock, clientAddr), daemon=True)
				cli.start()
			except socket.timeout: pass #The socket times out every second, so we have to catch this.

	def isRunning(self):
		return self.running

	def port():
		doc = "The port on which the server is operating."
		def fget(self): return self._port
		def fset(self, value): raise AttributeError("Cannot change the server's port property.")
		def fdel(self): raise AttributeError("Cannot delete the server's port property.")
		return locals()
	port = property(**port())

	def host():
		doc = "The hostname by which the server is identifying."
		def fget(self): return self._host
		def fset(self, value): raise AttributeError("Cannot change the server's hostname property.")
		def fdel(self): raise AttributeError("Cannot delete the server's hostname property.")
		return locals()
	host = property(**host())

	def encoder():
		doc = "The encoding function being used by the server."
		def fget(self): return self._encoder
		def fset(self, value): self._encoder = value
		def fdel(self): raise AttributeError("Cannot delete the server's encoder property.")
		return locals()
	encoder = property(**encoder())

	def decoder():
		doc = "The encoding function being used by the server."
		def fget(self): return self._decoder
		def fset(self, value): self._decoder = value
		def fdel(self): raise AttributeError("Cannot delete the server's decoder property.")
		return locals()
	decoder = property(**decoder())

	def socket():
		doc = "The socket on which the server is listening for new connections."
		def fget(self): return self._socket
		def fset(self, value): raise AttributeError("Cannot change the server's socket property.")
		def fdel(self): raise AttributeError("Cannot delete the server's socket property.")
		return locals()
	socket = property(**socket())

	def listen_timeout():
		doc = "How long the server waits when listening for new connections or input."
		def fget(self): return self._listen_timeout
		def fset(self, value):
			if self.isRunning():
				raise AttributeError("Cannot change the server's listen_timeout property while the server is running.")
			self._listen_timeout = value
		def fdel(self): raise AttributeError("Cannot delete the server's listen_timeout property.")
		return locals()
	listen_timeout = property(**listen_timeout())

	def socket_timeout():
		doc = "The timeout delay for sockets used by the server."
		def fget(self): return self._socket_timeout
		def fset(self, value):
			if self.isRunning():
				raise AttributeError("Cannot change the server's socket_timeout property while the server is running.")
			self._socket_timeout = value
		def fdel(self): raise AttributeError("Cannot delete the server's socket_timeout property.")
		return locals()
	socket_timeout = property(**socket_timeout())

	def socket_thread():
		doc = "The function that is run on the sockets created by the server."
		def fget(self): return self._socket_thread
		def fset(self, value):
			if self.isRunning():
				raise AttributeError("Cannot change the server's socket_thread property while the server is running.")
			self._socket_thread = value
		def fdel(self): raise AttributeError("Cannot delete the server's socket_thread property.")
		return locals()
	socket_thread = property(**socket_thread())

	def running():
		doc = "Whether the server is currently running."
		def fget(self):
			with self.__runningLock:
				return self._running
		def fset(self, value): raise AttributeError("Cannot change the server's running property.")
		def fdel(self): raise AttributeError("Cannot delete the server's running property.")
		return locals()
	running = property(**running())

	def __serverLoop(server, socket_thread, clientSock, clientAddr):
		try:
			while server.isRunning() and socket_thread(server, clientSock, clientAddr) == None: continue
		except Exception as e:
			server.log(e, "Client:", clientAddr, level='error')
		finally:
			sharedMethods.socketCloser(clientSock)

def getArgumentParser():
	parser = argparse.ArgumentParser(description='A simple IRC server.', formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument("-p", "--port", type=int, help="Sets the port on which the server should listen for incoming connections.", metavar='Port',
		default=6667, choices=helpers.TestableRange(6665, 6669, 'both', 1, int))
	parser.add_argument("--host", type=str, help="Sets the host of the server should listen for incoming connections.", metavar='Host', default="")
	parser.add_argument("-v", "--verbosity", type=int, help="Sets the verbosity of the server's log output.\n0: None, 1: errors, 2: warnings, 3: info\nIncreasing level adds scopes progressively.",
		metavar='Verb', default=0, choices=helpers.TestableRange(0, 3, 'both', 1, int))
	parser.add_argument("--listen-timeout", type=float, help="Sets the timeout on socket connections.", metavar='LT', default=5.0,
		choices=helpers.TestableRange(1.0, 300.0, 'both', 1.0, float), dest="listen_timeout")
	return parser
