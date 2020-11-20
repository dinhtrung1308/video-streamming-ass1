from tkinter import Button, Label, W, E, N, S, messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    # Define some constances
    INIT = 0
    READY = 1
    PLAYING = 2

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    state = INIT  # Initial state

    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)

        self.SETUP_STR = 'SETUP'
        self.PLAY_STR = 'PLAY'
        self.PAUSE_STR = 'PAUSE'
        self.TEARDOWN_STR = 'TEARDOWN'

        self.RTSP_VER = "RTSP/1.0"
        self.TRANSPORT = "RTP/UDP"

        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0

        # Statistic variables
        self.startTime = 0
        self.totalPlayTime = 0
        self.totalByte = 0
        self.lossPack = 0
        self.lossRate = 0
        self.dataRate = 0

        # --------------------

        # Remove SETUP button
        self.setupMovie()

    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        # self.setup = Button(self.master, width=20, padx=3, pady=3)
        # self.setup["text"] = "Setup"
        # self.setup["command"] = self.setupMovie
        # self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button

        self.start = Button(self.master, width=15, padx=10, pady=10, font=(
            '', 15, 'bold'), cursor='heart', fg="green")
        self.start["text"] = "PLAY"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=15, padx=10, pady=10, bg='#ffb3fe', font=(
            '', 15, 'bold'), cursor='heart', fg="#f5ac0f")
        self.pause["text"] = "PAUSE"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=15, padx=10, pady=10, bg='#ffb3fe', font=(
            '', 15, 'bold'), cursor='heart', fg="red")
        self.teardown["text"] = "TEARDOWN"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=10,
                        sticky=W + E + N + S, padx=5, pady=5)

        self.label4 = Label(self.master, text="Video time: ")
        self.label4.grid(row=2, column=1, padx=2, pady=2, sticky=W)
        self.labelTotalPlayTime = Label(self.master)
        self.labelTotalPlayTime.grid(row=2, column=2, padx=2, pady=2, sticky=W)

        self.label2 = Label(self.master, text="Loss rate: ")
        self.label2.grid(row=3, column=1, padx=2, pady=2, sticky=W)
        self.labelLostRate = Label(self.master)
        self.labelLostRate.grid(row=3, column=2, padx=2, pady=2, sticky=W)

        self.label3 = Label(self.master, text="Data rate: ")
        self.label3.grid(row=4, column=1, padx=2, pady=2, sticky=W)
        self.labelDataRate = Label(self.master)
        self.labelDataRate.grid(row=4, column=2, padx=2, pady=2, sticky=W)

        self.label1 = Label(self.master, text="Total byte received: ")
        self.label1.grid(row=5, column=1, padx=2, pady=2, sticky=W)
        self.labelTotalByte = Label(self.master)
        self.labelTotalByte.grid(row=5, column=2, padx=2, pady=2, sticky=W)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        # Delete the cache image from video
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

    def pauseMovie(self):
        """Pause button handler."""

        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)
            self.startTime = time.time()

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)

                # -----------------------------
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    print("Received frame", currFrameNbr)

                    # Calculate statistics
                    # Time
                    self.totalPlayTime += time.time() - self.startTime
                    self.startTime = time.time()
                    # Total data
                    self.totalByte += len(data)
                    # Data rate
                    self.dataRate = 0 if self.totalPlayTime == 0 else (
                        self.totalByte / self.totalPlayTime)
                    # Lost rate
                    if (currFrameNbr - self.frameNbr > 1):
                        self.lossPack = self.lossPack + currFrameNbr - self.frameNbr - 1
                    self.lossRate = self.lossPack / currFrameNbr

                    # ----------------------------------------------------
                    if currFrameNbr > self.frameNbr:  # Discard the old packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(
                            rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    try:
                        self.rtpSocket.shutdown(socket.SHUT_RDWR)
                        self.rtpSocket.close()
                    except:
                        pass
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()
        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

        self.labelTotalByte['text'] = str(self.totalByte) + " bytes"
        self.labelLostRate['text'] = "{:.2f}".format(self.lossRate)
        self.labelDataRate['text'] = "{:.2f} bytes/s".format(self.dataRate)
        self.labelTotalPlayTime['text'] = "{:.2f} s".format(self.totalPlayTime)

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            messagebox.showwarning(
                'Connection Failed', 'Connection to \'{}\' failed.'.format(self.serverAddr))

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            self.rtspSeq = self.rtspSeq + 1
            request = "{} {} {}\nCSeq: {}\nTransport: {}; client_port: {}".format(
                self.SETUP_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.TRANSPORT, self.rtpPort)
            self.requestSent = self.SETUP

        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq = self.rtspSeq + 1
            request = "{} {} {}\nCSeq: {}\nSession: {}".format(
                self.PLAY_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)
            self.requestSent = self.PLAY

        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq = self.rtspSeq + 1
            request = "{} {} {}\nCSeq: {}\nSession: {}".format(
                self.PAUSE_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)
            self.requestSent = self.PAUSE

        elif requestCode == self.TEARDOWN:
            self.rtspSeq = self.rtspSeq + 1
            request = "{} {} {}\nCSeq: {}\nSession: {}".format(
                self.TEARDOWN_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)
            self.requestSent = self.TEARDOWN
        else:
            return

        self.rtspSocket.send(request.encode())

        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply)

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split(b'\n')
        seqNum = int(lines[1].split(b' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(b' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            if self.sessionId == session and int(lines[0].split(b' ')[1]) == 200:

                if self.requestSent == self.SETUP:
                    self.state = self.READY
                    self.openRtpPort()

                elif self.requestSent == self.PLAY:
                    self.state = self.PLAYING

                elif self.requestSent == self.PAUSE:
                    self.state = self.READY
                    self.playEvent.set()

                elif self.requestSent == self.TEARDOWN:
                    self.state = self.INIT
                    self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.rtpSocket.settimeout(0.5)

        try:
            self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
        except:
            messagebox.showwarning(
                'Unable to Bind', 'Unable to bind PORT={}'.format(self.rtpPort))

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if messagebox.askokcancel("Quit?", "Are you really want to quit?"):
            self.exitClient()
