'''

David Lettier (C) 2014.

Simple chat server. Use Telnet as the client.

Python 2.7.3.

'''

# Imports.

import socket;
import threading;
import ctypes;
import time;
import os;
import Queue;
import sys;
import select;
import re;

# Thread class used to detect user input and if the user input does match 
# the character that is being looked for, set the flag true. 

class User_Reponse_Thread( threading.Thread ):

	def __init__( self, rFlags, rFlagKey, cCheck ):
	
		# Initialize the thread.
	
		threading.Thread.__init__( self );
		
		# Flags to set.
	
		self.response_flags = rFlags;
		
		# Flag key since flags is a dictionary.
		
		self.response_flag_key = rFlagKey;
		
		# Character to check for in order to set the flag true or false.
		
		self.character_to_check_for = cCheck;
		
	def run( self ):
	
		# Run loop.
	
		while 1:
	
			user_input = raw_input( "" );
		
			if user_input[ 0 ] == self.character_to_check_for:
		
				self.response_flags[ self.response_flag_key ] = True;

# Client thread class for handling the client sockets.

class Client_Thread( threading.Thread ):
	
	def __init__( self, IP, port, cSocket, mQueues, uNames, cKey ):
	
		# Initialize the thread.
	
		threading.Thread.__init__( self );
		
		# Message queues which is a dictionary of queues.
		# Each client thread has its own message queue that it
		# reads from so that what one client says can be read 
		# by all clients.
		
		self.message_queues = mQueues;
		
		# User names dictionary where each value is a list consisting of [user_name,IP].
		
		self.user_names = uNames;
		
		# This client's key to both the message queue dictionary and the user names dictionary.
		
		self.client_key = cKey;
		
		# This client's user name for use in the chat room.
		
		self.user_name = None;
		
		# System call to get the actual thread ID.
		
		SYS_gettid = 186;
		
		libc = ctypes.cdll.LoadLibrary( "libc.so.6" );
		
		self.thread_id = libc.syscall( SYS_gettid );
		
		# IP address of the socket.
		
		self.IP = IP;
		
		# Port number of the socket.
		
		self.port = port;
		
		# The client socket.
		
		self.client_socket = cSocket;
		
		# Non blocking recv.
		
		self.client_socket.setblocking( 0 );
		
	def __get_number_of_repeated_user_names( self ):
	
		# Matches the requested user name to any user name already in use.
	
		count = 0;
		
		matcher = re.compile( "(" + str( self.user_name ) + "$)" + "|" + "(" + self.user_name + "\s\([0-9]+\)" + ")", re.IGNORECASE );
		
		for k, v in self.user_names.iteritems( ):
		
			if v != None:
		
				if matcher.match( self.user_names[ k ][ 0 ] ) != None:
	
					count = count + 1;
				
		return count;
		
	def __send_user_names_to_client_socket( self ):
	
		# Sends a list of users' names that are currently chatting.
	
		user_names = "\nUsers:\n";
	
		for k, v in self.user_names.iteritems( ):
		
			if v != None:
			
				user_names = user_names + "\t" + ": ".join( self.user_names[ k ] ) + "\n";
		
		self.client_socket.send( user_names );
		
	def __send_message_to_client_socket( self, message ):
	
		# Send a message to a client.
	
		try:
		
			self.client_socket.send( message );
			
		except:
		
			# Broken pipe.
			
			pass;
		
	def __propagate_message_to_all_client_message_queues( self, message ):
	
		# For use by all client threads where each thread has its own queue in the
		# message queue dictionary.
		
		# This puts the message in each client thread's message queue.
	
		for k, v in self.message_queues.iteritems( ):
		
			if v != None:
			
				self.message_queues[ k ].put( message );
				
	def __flush_client_message_queue_to_client_socket( self ):
	
		# Send all the messages in this client's message queue to the client socket.
	
		while 1:
		
			try:
			
				broadcast_message = self.message_queues[ self.client_key ].get( False );
				
				try:
	
					self.client_socket.send( broadcast_message );
					
				except:
				
					# Broken pipe.
					
					pass;
	
			except Queue.Empty:

				break;
		
	def run( self ):
	
		# Thread run loop.
		
		# Only ask the client for their desired user name once.
	
		asked_for_user_name = 0;
	
		while 1:
		
			# If they don't have a user name, get it.
			
			if self.user_name == None:
			
				# Ask once.
			
				if asked_for_user_name == 0:
	
					self.client_socket.send( "\nWelcome. What is your username?\n" );
				
					asked_for_user_name = 1;
					
				# Any data on the client socket?
				
				ready = select.select( [ self.client_socket ], [ ], [ ], 1 );
				
				if ready[ 0 ]:
				
					# Read in the data from the socket.
	
					client_data = "";
	
					while 1:

						buffer = self.client_socket.recv( 1024 );
						
						if buffer == "":
						
							# Closed socket.
						
							break;

						if ( buffer.find( "\n" ) != -1 ): 
	
							client_data = client_data + buffer;
				
							break;
				
						else:
			
							client_data = client_data + buffer;
							
					# Closed socket?
					
					if client_data == "":
					
						# They must of shut down their client without sending any data.
						
						# Set their user name as anonymous.
					
						self.user_name = "Anonymous";
						
						# Get repeat user names.
						
						number = self.__get_number_of_repeated_user_names( );
						
						# Set their user name as a their desired user name plus a unique 
						# integer identifier if needed.
						
						if number != 0:
						
							self.user_name = self.user_name + " (" + str( number ) + ")";
							
						# Let the other clients know of this client's user name.
					
						self.user_names[ self.client_key ] = [ self.user_name, str( self.IP ) ];
						
						# Tell every client of their arrival.
		
						self.__propagate_message_to_all_client_message_queues( "\n**" + self.user_name + " has joined the conversation.**\n" ); 
						
						# Flush any messages to this client that has been sent from other clients.
						
						self.__flush_client_message_queue_to_client_socket( );
						
					else:
					
						# Get user name.

						self.user_name = str( client_data ).split( " " )[ 0 ].replace( "\r", "" ).replace( "\n", "" );
						
						# Detect and set unique user name if needed.
						
						number = self.__get_number_of_repeated_user_names( );
						
						if number != 0:
						
							self.user_name = self.user_name + " (" + str( number ) + ")";
							
						# Tell the others of this client's user name and their arrival to the chat.
					
						self.user_names[ self.client_key ] = [ self.user_name, str( self.IP ) ];
		
						self.__propagate_message_to_all_client_message_queues( "\n**" + self.user_name + " has joined the conversation.**\n" ); 
						
						# Send a welcome message just to this client only.
						
						self.__send_message_to_client_socket( "\nHello " + self.user_name + "! You may begin sending messages now. Type !quit! to exit. Type !users! to see who is apart of the conversation.\n" );
						
						# Flush any messages that other clients have sent to this client.
			
						self.__flush_client_message_queue_to_client_socket( );
				
			else:
			
				# Their user name is set.
				
				# Detect if there is any data to read.
				
				ready = select.select( [ self.client_socket ], [ ], [ ], 1 );
				
				if ready[ 0 ]:
				
					# There is data to read.
				
					client_data = "";
	
					while 1:

						buffer = self.client_socket.recv( 1024 );
						
						if buffer == "":
						
							break;

						if buffer.find( "\n" ) != -1: 
	
							client_data = client_data + buffer;
				
							break;
				
						else:
			
							client_data = client_data + buffer;
							
					# Closed socket?
					
					if client_data == "":
					
						# Looks like they closed abruptly.
					
						client_data = "!quit!";
							
					# Client quit?
							
					if client_data.find( "!quit!" ) != -1:
					
						# They want to quit so let others know of their departure.
						
						self.__propagate_message_to_all_client_message_queues( "\n**" + self.user_name + " has left the conversation.**\n" );
						
						# Flush any remaining messages to this client before they go.
							
						self.__flush_client_message_queue_to_client_socket( );
						
						# Remove their queue from the message queue dictionary.
							
						self.message_queues[ self.client_key ] = None;
						
						del self.message_queues[ self.client_key ];
						
						# Remove their user name key,value from the dictionary of user names.
						
						self.user_names[ self.client_key ] = None;
						
						del self.user_names[ self.client_key ];
						
						# Exit run loop.
						
						break;
						
					elif client_data.find( "!users!" ) != -1:
					
						# They want the list of current users so send the list.
					
						self.__send_user_names_to_client_socket( );
						
					else:
					
						# They said something so send it to all clients.
		
						self.__propagate_message_to_all_client_message_queues( "\n" + self.user_name + ": " + client_data + "\n" );
						
				else:
				
					# No data to read so flush any messages sent by other clients.
					
					self.__flush_client_message_queue_to_client_socket( );
					
		# End of the run loop so close the socket.
						
		self.client_socket.close( );
		
# Intro message.
			
print "\nWelcome to Chatty Kathy Server 5555! Press [q] to quit.\n";

# Detect if the user wants to shut down the server.

response_flags = { "quit": False }

user_response_thread = User_Reponse_Thread( response_flags, "quit", "q" );

user_response_thread.daemon = True;

user_response_thread.setDaemon( True );

user_response_thread.start( );

# Setup a dictionary that will contain a message queue per client currently chatting.

message_queues = { };

# Setup a dictionary of user names for all clients currently chatting.

user_names = { };

# This will generate the unique client key for use in the shared dictionaries.

current_milliseconds = lambda: int( round( time.time( ) * 1000 ) );

# Setup socket and begin listening for requests.

host = socket.gethostname( ); # Local host name. Should be the name of your machine.
port = 5555;

server_socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM );

server_socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 );

server_socket.bind( ( host, port ) );

server_socket.listen( 5 );

# Do not block when listening for a client connection.

server_socket.settimeout( 1 );

print "Server listening on: " + socket.gethostbyname( socket.gethostname( ) ) + ":" + str( port ) + "\n";

# Handle connections as they come in by passing them off to a thread.

while 1:

	# Shutdown server?

	if response_flags[ "quit" ] == True:
	
		# If no users currently chatting, just shutdown. Otherwise let all users know that the server is closing.
	
		if len( user_names ) != 0:
	
			print "\nServer closing in 5 seconds.\n";
		
			for k, v in message_queues.iteritems( ):
		
				if v != None:
			
					message_queues[ k ].put( "\n**Server closing in 5 seconds.**\n" );
				
			time.sleep( 5 );
	
			server_socket.close( );
		
			break;
			
		else:
		
			server_socket.close( );
		
			break;

	# Accept the request.
	
	try:

		( client_socket, ( IP, port ) ) = server_socket.accept( );
		
	except socket.timeout:
	
		# Non-blocking.

		continue;
		
	# Incoming client connection status message.

	print "\nNew client connection.";
	print "IP: " + IP;
	
	# Generate unique client key for use in the shared dictionaries.
	
	client_key = current_milliseconds( );
	
	# Setup this client with its own message queue.
	
	message_queues[ client_key ] = Queue.Queue( );
	
	# Setup this client with its own user name entry.
	
	user_names[ client_key ] = None;
	
	# Total clients connected status message.
	
	print "\nCurrent number of clients: " + str( len( message_queues ) );
	
	# Initialize the client thread and run it.

	client_thread = Client_Thread( IP, port, client_socket, message_queues, user_names, client_key );
	
	client_thread.daemon = True;
	
	client_thread.setDaemon( True );

	client_thread.start( );
	
# Shutdown server gracefully.
	
print "\nServer closed.\n";
	
sys.exit( 0 );
