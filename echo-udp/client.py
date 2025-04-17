import socket

def main():
    # Server configuration
    host = '127.0.0.1'  # The server's hostname or IP address
    port = 65433        # The port used by the UDP server
    
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        print(f"UDP client ready to send messages to {host}:{port}")
        
        while True:
            # Get user input
            message = input("Enter message (or 'exit' to quit): ")
            
            # Check if user wants to exit
            if message.lower() == 'exit':
                break
            
            # Send the message to the server
            client_socket.sendto(message.encode(), (host, port))
            
            # Set a timeout for receiving response
            client_socket.settimeout(5)
            
            try:
                # Receive the response from the server
                data, server = client_socket.recvfrom(1024)
                
                # Print the response
                print(f"Received: {data.decode()}")
            
            except socket.timeout:
                print("Request timed out")
    
    print("Client closed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nClient shutting down...")