import socket
import threading
import sys

# Dictionary to store client connections and usernames
clients = {}
clients_lock = threading.Lock()

def broadcast(message, sender_conn=None):
    """Send message to all clients except the sender"""
    with clients_lock:
        for conn, username in clients.items():
            if conn != sender_conn:
                try:
                    conn.sendall(message.encode())
                except:
                    # Remove failed connection later
                    pass

def handle_client(conn, addr):
    """Handle individual client connection"""
    username = None
    
    try:
        # First message should be the username
        initial_msg = conn.recv(1024).decode()
        if initial_msg.startswith("USERNAME:"):
            username = initial_msg[9:]
            with clients_lock:
                clients[conn] = username
            print(f"{username} connected from {addr}")
            broadcast(f"{username} has joined the chat", conn)
        else:
            username = f"Guest_{addr[0]}_{addr[1]}"
            with clients_lock:
                clients[conn] = username
            print(f"{username} connected from {addr}")
            broadcast(f"{username} has joined the chat", conn)
        
        # Main message handling loop
        while True:
            try:
                msg = conn.recv(1024)
                if not msg:
                    break
                    
                decoded_msg = msg.decode()
                print(f"{username}: {decoded_msg}")
                broadcast(f"{username}: {decoded_msg}", conn)
                
            except ConnectionResetError:
                break
                
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    
    finally:
        # Clean up when client disconnects
        print(f"{username} disconnected")
        with clients_lock:
            if conn in clients:
                del clients[conn]
        broadcast(f"{username} has left the chat")
        conn.close()

def main():
    HOST = '127.0.0.1'
    PORT = 12345
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow socket to be reused immediately after closing
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"Server started on {HOST}:{PORT}")
        print("Waiting for connections...")
        
        while True:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break
            except Exception as e:
                print(f"Error accepting connection: {e}")
    
    except Exception as e:
        print(f"Server error: {e}")
    
    finally:
        # Clean up all connections
        with clients_lock:
            for conn in list(clients.keys()):
                try:
                    conn.close()
                except:
                    pass
        server_socket.close()
        print("Server shut down")

if __name__ == "__main__":
    main()