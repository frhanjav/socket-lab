import socket

def main():
    # Server configuration
    host = '127.0.0.1'  # localhost
    port = 65433        # Different port from TCP server
    
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        # Bind the socket to the address
        server_socket.bind((host, port))
        
        print(f"UDP Server is listening on {host}:{port}")
        
        while True:
            # Receive data and address from client
            data, client_address = server_socket.recvfrom(1024)
            
            # Print received message
            print(f"Received from {client_address}: {data.decode()}")
            
            # Capitalize the message
            capitalized_data = data.decode().upper().encode()
            
            # Send capitalized data back to client
            server_socket.sendto(capitalized_data, client_address)
            print(f"Sent to {client_address}: {capitalized_data.decode()}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer shutting down...")