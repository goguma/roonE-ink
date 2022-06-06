import asyncio
import threading
import time
from pprint import pprint
import requests

from ePaper import ePaper
from ups import UPS

statusUpdated = threading.Event()
statusUpdateFlag = False
statusUpdatelock = threading.Lock()
roonStatus = None

class Roon(threading.Thread):
    def __init__(self, address="localhost", port=3000):

        threading.Thread.__init__(self)
        self.address = address
        self.port = port

        from socketIO_client import SocketIO

        self._state = {}
        self._queue = list()
        self._radios = list()
        self._waiting = .1

        print("Creating socket {address}:{port}".format(address=address, port=port))
        self._sock = SocketIO(address, port)

        self._sock.on('pushState', self._on_push_state)

        print("Getting initial state")
        self.get_state()

    def run(self):
        print("roon subthread is started")
        print('wait until get roon status')
        # time.sleep(10)
        # self.get_state()
        self._sock.wait()
        print("roon subthread is ended")

    def _on_push_state(self, *args):
        print("State updated")
        self._state = args[0]
        # pprint(self._state)
        global roonStatus
        global statusUpdateFlag
        statusUpdatelock.acquire()
        roonStatus = self._state
        statusUpdateFlag = True
        statusUpdatelock.release()

def main():
    updateScreenFlag = False
    album = None
    title = None
    artist = None
    albumArtURI = None

    th = Roon('localhost', '3000')
    th.start()  # run()에 구현한 부분이 실행된다

    batteryModule = UPS()
    screenModule = ePaper()

    lastCapacity = 0

    while True:
        statusUpdated.wait(1)

        global statusUpdateFlag
        global roonStatus

        if statusUpdateFlag == True:
            print('roon status updated')
            if updateScreenFlag == False:
                updateScreenFlag = True

            if len(roonStatus['album']):
                album = roonStatus['album']
            if len(roonStatus['title']):
                title = roonStatus['title']
            if len(roonStatus['artist']):
                artist = roonStatus['artist']
            albumArtURI = roonStatus['albumart']

            if len(album) == 0 or len(title) == 0 or len(artist) == 0:
                updateScreenFlag = False

            statusUpdatelock.acquire()
            statusUpdateFlag = False
            statusUpdatelock.release()

        capacity = batteryModule.readCapacity()
        capacity = round(capacity, 0)
        if lastCapacity != capacity:
            lastCapacity = capacity
            print('capacity : {}'.format(capacity))
            print('update ePaper')

            if updateScreenFlag == False:
                updateScreenFlag = True

        if updateScreenFlag == True:
            screenModule.clearScreen()

            print('albumArtURI : {}'.format(albumArtURI))
            if (albumArtURI != None and albumArtURI.startswith('http')):
                screenModule.drawImage(0, 0, 96, 96, requests.get(albumArtURI, stream=True).raw)

            screenModule.drawText(100, 0, 15, album)
            screenModule.drawText(100, 30, 24, title)
            screenModule.drawText(100, 60, 15, artist)

            capacity = 'BAT : {}%'.format(capacity)
            screenModule.drawText(185, 100, 15, capacity)

            screenModule.flush()
            updateScreenFlag = False
    th.join()

if __name__ == "__main__":
    main()
