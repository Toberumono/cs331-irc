import sys, socket, select, re
import threading, subprocess, os.path
from helpers import *

debugger = ThreeStateLogger(0)
default = {
	'timeout' : 5.0,
	'format' : 'ascii',
	'buffersize' : 1024,
	'executable' : subprocess.check_output("which bash", shell=True, universal_newlines=True).strip(), #This just gets the location of bash
	'editor' : os.environ.get('EDITOR','vim')
}
regexes = {'special' : r'[\[\]\{\}\\`_^|]'

def setVerbosity(verbosity):
	debugger = ThreeStateLogger(verbosity)

'''
Just avoids repeated code by forwarding to subprocess.check_output with shell and universal_newlines set to True.
'''
def simpleSubprocess(args, executable=default['executable']):
	return subprocess.check_output(args, executable=executable, shell=True, universal_newlines=True)

'''
This is used so that we can guarantee that we will get something to send back to the user
while also internally reporting any decoding errors if they occur.
'''
def decoder(decodeable, format=default['format']):
	try:
		return decodeable.decode(format)
	except Exception as e:
		debugger.log(e, level="warning")
		return decodeable.decode(format, 'ignore')

'''
This is used so that we can guarantee that we will get something to send back to the user
while also internally reporting any encoding errors if they occur.
'''
def encoder(encodeable, format=default['format']):
	try:
		return encodeable.encode(format)
	except Exception as e:
		debugger.log(e, level="warning")
		return encodeable.encode(format, 'ignore')

'''
This method handles the logic that forwards messages from the client to another server.
This allows for the client to send a single selector string that is recursively passed
	from this server to others as the .links files indicate.
'''
def serverForward(message, address, port, encoder=encoder, decoder=decoder):
	serverSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	serverSock.connect((address, port))
	debugger.log("Forwarding to:", address + ':' + str(port), level="info")

	serverSock.send(encoder(message))
	debugger.log("Sent message; waiting for reply", level="info")
	out = getSocketResponse(sock=serverSock)
	socketCloser(serverSock)
	return out

'''
Uses timeoutRecv to read from a socket until the received data satisfies termination_test or
	if there is nothing to read from the socket after the timeout period has expired.
NOTE: The timeout resets after each read, so it is inadvisable to use this function for anything
	time-sensitive.
NOTE: The input is run through decoder prior to being passed to termination_test.
This function will timeout if there is no data available after the given timeout time.
'''
def getSocketResponse(sock, buffersize=default['buffersize'], timeout=default['timeout'], decoder=decoder, termination_test=lambda x: x.endswith("\n.")):
	output = ""
	while not termination_test(output):
		data = timeoutRecv(sock=sock, buffersize=buffersize, timeout=timeout)
		if not len(data):
			break
		output += decoder(data)
	return output

'''
This implements a timeout on the recv method for the given socket.
The buffersize and timeout parameters all have default values that are consistent with the
	values used throughout the server code.
This method will either return the raw bytes from the socket up to buffersize or raise a
	socket.timeout exception after the timeout period has expired if there is nothing to
	read from the socket.
'''
def timeoutRecv(sock, buffersize=default['buffersize'], timeout=default['timeout']):
	ready = select.select([sock], [], [], timeout)
	if ready[0]:
		return sock.recv(buffersize)
	else:
		raise socket.timeout('Socket timed out after', timeout, 'seconds.')

'''
It is proper form to shut down a socket before closing it.
However, it is possible for that method to fail on sockets that were already partially closed,
	necessitating a try-except block, which is a multi-line construct and would otherwise require
	a bunch of copy-paste.  Therefore, we moved it into this method.
'''
def socketCloser(sock):
	try:
		sock.shutdown(socket.SHUT_RDWR)
	except OSError:
		try:
			debugger.log("Socket for", sock.getpeername(), "was already shut down.", level="warning")
		except OSError:
			debugger.log("Socket was never connected.", level="warning")
	sock.close()
