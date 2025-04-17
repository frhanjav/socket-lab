import socket

def main():
    # Server configuration
    host = '127.0.0.1'  # localhost
    port = 65432        # Port to listen on (non-privileged ports are > 1023)
    
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Bind the socket to the address
        server_socket.bind((host, port))
        # Enable the server to accept connections
        server_socket.listen()
        
        print(f"TCP Server is listening on {host}:{port}")
        
        while True:
            # Wait for a connection
            client_socket, client_address = server_socket.accept()
            print(f"Connected by {client_address}")
            
            with client_socket:
                while True:
                    # Receive data from the client
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    # Print received message
                    print(f"Received: {data.decode()}")
                    
                    # Capitalize the message and send it back
                    capitalized_data = data.decode().upper().encode()
                    client_socket.sendall(capitalized_data)
                    print(f"Sent: {capitalized_data.decode()}")
            
            print(f"Connection with {client_address} closed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer shutting down...")