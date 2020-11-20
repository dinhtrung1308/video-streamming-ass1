# video-streamming-ass1
USER MANUAL:
- First, start the server with the command line:

#python Server.py server_port

Where: 
•	server_port is the port your server listens to for incoming RTSP connections.
•	The standard RTSP port is 554, but you need to choose a port number greater than 1024.
-	Next, open a new terminal, then start the client with the command line:


#python ClientLauncher.py  server_host server_port RTP_port video_file


Where: 
•	server_host is the name of the machine where the server is running. You can use #ipconfig to find your IP address.
•	server_port is the port your server listens to for incoming RTSP connections.
•	RTP_port is the port where the RTP packets are received (here “5008”)
•	video_file: name of video file you want to request here.
SETUP function:
• Send SETUP request to the server. You will need to insert the Transport header in which you specify the port for the RTP data socket you just created. 
• Read the server’s response and parse the Session header (from the response) to get the RTSP session ID. 
• Create a datagram socket for receiving RTP data and set the timeout on the socket to 0.5 seconds.
PLAY function:
• Send PLAY request. You must insert the Session header and use the session ID returned in the SETUP response. You must not put the Transport header in this request. 
• Read the server's response.
PAUSE function:
• Send PAUSE request. You must insert the Session header and use the session ID returned in the SETUP response. You must not put the Transport header in this request. 
• Read the server's response.
TEARDOWN function:
• Send TEARDOWN request. You must insert the Session header and use the session ID returned in the SETUP response. You must not put the Transport header in this request. 
• Read the server's response. 



 



