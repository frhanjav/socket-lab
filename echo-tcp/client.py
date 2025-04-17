import socket

def main():
    # Server configuration
    host = '127.0.0.1'  # The server's hostname or IP address
    port = 65432        # The port used by the server
    
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        # Connect to the server
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
        
        while True:
            # Get user input
            message = input("Enter message (or 'exit' to quit): ")
            
            # Check if user wants to exit
            if message.lower() == 'exit':
                break
            
            # Send the message to the server
            client_socket.sendall(message.encode())
            
            # Receive the response from the server
            data = client_socket.recv(1024)
            
            # Print the response
            print(f"Received: {data.decode()}")
    
    print("Connection closed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except ConnectionRefusedError:
        print("Connection failed. Make sure the server is running.")