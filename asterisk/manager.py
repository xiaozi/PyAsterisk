import socket, threading, Queue

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

		self._messageQueue = Queue.Queue()
		self._eventQueue = Queue.Queue()
		self._responseQueue = Queue.Queue()

		self.messageThread = threading.Thread(target=self.dispatchMessage)
		self.messageThread.setDaemon(True)

		self.eventThread = threading.Thread(target=self.dispatchEvent)
		self.messageThread.setDaemon(True)

		# self.responseThread = threading.Thread(target=self.dispatchMessage)
		# self.messageThread.setDaemon(True)

	def close(self):
		self.messageThread.join()
		self.eventThread.join()
		# self.responseThread.join()

	def connect(self, host, port = 5038):
		_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		_socket.connect((host, port))
		self._socket = _socket

		self.messageThread.start()
		self.eventThread.start()

	def login(self, username, secret):
		self.sendAction({
			'Action': 'Login',
			'UserName': username,
			'Secret': secret,
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
				continue
			fields = Message().parse(message)
			if 'Event' in fields:
				self._eventQueue.put(fields)
			if 'Response' in fields:
				self._responseQueue.put(fields)

		readThread.join()

	def dispatchEvent(self):
		while True:
			event = self._eventQueue.get()
			if not event:
				continue
			
			print(event)
			

	def read(self):
		EOLLength = len(Message.EOL)
		EOMLength = len(Message.EOM)

		buff = self._socket.recv(1024)
		currentMessage = buff[buff.find(Message.EOL) + EOLLength: ]

		while True:
			buff = self._socket.recv(65535)
			if not buff:
				break
			currentMessage += buff
			EOMPosition = currentMessage.find(Message.EOM)
			if EOMPosition == -1:
				continue
			message = currentMessage[0: EOMPosition]
			currentMessage = currentMessage[EOMPosition + EOMLength: ]
			self._messageQueue.put(message)


if __name__ == '__main__':
	manager = Manager()
	manager.connect('127.0.0.1')
	manager.login('xiaozi', 'born1990')

	manager.close()