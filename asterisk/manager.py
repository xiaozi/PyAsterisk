import socket, threading, Queue
import time

class Message(object):
	SEP = ':'
	EOL = '\r\n'
	EOM = '\r\n\r\n'

	def parse(self, message):
		lines = message.split(self.EOL)
		fields = {}
		for line in lines:
			tmp = line.split(self.SEP, 1)
			fields[tmp[0]] = tmp[1].strip()
		return fields


class Manager(object):
	def __init__(self):
		self._socket = None
		self._connected = threading.Event()

		self._messageQueue = Queue.Queue()
		self._eventQueue = Queue.Queue()
		# self._responseQueue = Queue.Queue()
		
		self._callbacks = {}

		self._messageThread = threading.Thread(target=self.dispatchMessage)
		self._messageThread.setDaemon(True)

		self._eventThread = threading.Thread(target=self.dispatchEvent)
		self._eventThread.setDaemon(True)

		# self._responseThread = threading.Thread(target=self.dispatchResponse)
		# self._responseThread.setDaemon(True)

	def loop(self):
		self._messageThread.join()
		self._eventThread.join()
		# self._responseThread.join()

	def connect(self, host, port = 5038):
		_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		_socket.connect((host, port))
		self._socket = _socket
		self._connected.set()

		self._messageThread.start()
		self._eventThread.start()
		# self._responseThread.start()

	def close(self):
		if self._connected.isSet():
			self.logoff()
			self._connected.clear()
		self._messageQueue.put(None)
		self._messageThread.join()
		if threading.currentThread() != self._eventThread:
			self._eventThread.join()

	def login(self, username, secret):
		self.sendAction({
			'Action': 'Login',
			'UserName': username,
			'Secret': secret,
		})

	def logoff(self):
		self.sendAction({
			'Action': 'Logoff'
		})

	def sendAction(self, command):
		command = Message.EOL.join([Message.SEP.join(pair) for pair in command.items()]) + Message.EOM

		self._socket.send(command)

	def dispatchMessage(self):
		readThread = threading.Thread(target=self.read)
		readThread.setDaemon(True)
		readThread.start()
		
		while True:
			message = self._messageQueue.get()
			if not message:
				self._eventQueue.put(None)
				# self._responseQueue.put(None)
				break
			fields = Message().parse(message)
			if 'Event' in fields:
				self._eventQueue.put(fields)
			'''
			if 'Response' in fields:
				self._responseQueue.put(fields)
			'''

		readThread.join()

	def dispatchEvent(self):
		while True:
			event = self._eventQueue.get()
			if not event:
				break

			callbacks = (self._callbacks.get(event['Event'], [])) + (self._callbacks.get('*', []))

			for callback in callbacks:
				if callback(event, self):
					break
	'''	
	def dispatchResponse(self):
		while True:
			response = self._responseQueue.get()
			if not response:
				break
			print(response)
	'''
	
	def registerEvent(self, event, func):
		callbacks = self._callbacks.get(event, [])
		callbacks.append(func)
		self._callbacks[event] = callbacks

	def unregisterEvent(self, event, func):
		callbacks = self._callbacks.get(event, [])
		callbacks.remove(func)
		self._callbacks[event] = callbacks

	def read(self):
		EOLLength = len(Message.EOL)
		EOMLength = len(Message.EOM)

		buff = self._socket.recv(1024)
		currentMessage = buff[buff.find(Message.EOL) + EOLLength: ]

		while self._connected.isSet():
			buff = self._socket.recv(65535)
			if not buff:
				break
			currentMessage += buff

			EOMPosition = currentMessage.find(Message.EOM)
			while EOMPosition != -1:
				message = currentMessage[0: EOMPosition]
				currentMessage = currentMessage[EOMPosition + EOMLength: ]
				EOMPosition = currentMessage.find(Message.EOM)
				self._messageQueue.put(message)
	def __del__(self):
		self.close()
def eventHandler(event, manager):
	print(event['Exten'], ': ', event['Status'])

if __name__ == '__main__':
	manager = Manager()

	manager.connect('127.0.0.1')
	manager.login('xiaozi', 'born1990')

	manager.registerEvent('ExtensionStatus', eventHandler)
	# manager.loop()
	
	# sample
	time.sleep(20)
	# your can trigger the close method somewhere.
	# manager.close()