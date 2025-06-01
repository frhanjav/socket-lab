import socket
import threading
import sys
from hamming import HammingCodec

# Dictionary to store client connections and usernames
clients = {}
clients_lock = threading.Lock()

def broadcast(message, sender_conn=None):
    """Send message to all clients except the sender with Hamming encoding and error injection"""
    if not message:
        return
    
    message_bytes = message.encode('utf-8')
    
    with clients_lock:
        for conn, username in clients.items():
            if conn != sender_conn:
                try:
                    # Encode message with Hamming code
                    encoded_data = HammingCodec.encode_bytes(message_bytes)
                    print(f"[SERVER] Original message size: {len(message_bytes)} bytes")
                    print(f"[SERVER] Encoded message size: {len(encoded_data)} bytes")
                    
                    # Introduce a random single-bit error
                    corrupted_data = HammingCodec.introduce_random_error(encoded_data)
                    
                    # Send length first, then the corrupted encoded data
                    length_bytes = len(corrupted_data).to_bytes(4, byteorder='big')
                    conn.sendall(length_bytes + corrupted_data)
                    
                except Exception as e:
                    print(f"[SERVER] Error sending to {username}: {e}")
                    # Remove failed connection later
                    pass

def handle_client(conn, addr):
    """Handle individual client connection"""
    username = None
    
    try:
        # First message should be the username
        # Receive length first
        length_bytes = conn.recv(4)
        if len(length_bytes) != 4:
            print(f"[SERVER] Failed to receive length from {addr}")
            return
        
        message_length = int.from_bytes(length_bytes, byteorder='big')
        
        # Receive the encoded message
        encoded_data = b''
        while len(encoded_data) < message_length:
            chunk = conn.recv(message_length - len(encoded_data))
            if not chunk:
                break
            encoded_data += chunk
        
        if len(encoded_data) != message_length:
            print(f"[SERVER] Incomplete message from {addr}")
            return
        
        # Decode the Hamming-encoded username message
        decoded_bytes, errors = HammingCodec.decode_bytes(encoded_data)
        if errors:
            print(f"[SERVER] Corrected errors in username message: {errors}")
        
        initial_msg = decoded_bytes.decode('utf-8')
        
        if initial_msg.startswith("USERNAME:"):
            username = initial_msg[9:]
            with clients_lock:
                clients[conn] = username
            print(f"[SERVER] {username} connected from {addr}")
            broadcast(f"{username} has joined the chat", conn)
        else:
            username = f"Guest_{addr[0]}_{addr[1]}"
            with clients_lock:
                clients[conn] = username
            print(f"[SERVER] {username} connected from {addr}")
            broadcast(f"{username} has joined the chat", conn)
        
        # Main message handling loop
        while True:
            try:
                # Receive length first
                length_bytes = conn.recv(4)
                if len(length_bytes) != 4:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                if message_length == 0:
                    break
                
                # Receive the encoded message
                encoded_data = b''
                while len(encoded_data) < message_length:
                    chunk = conn.recv(message_length - len(encoded_data))
                    if not chunk:
                        break
                    encoded_data += chunk
                
                if len(encoded_data) != message_length:
                    break
                
                # Decode the Hamming-encoded message
                decoded_bytes, errors = HammingCodec.decode_bytes(encoded_data)
                if errors:
                    print(f"[SERVER] Corrected errors from {username}: {errors}")
                
                decoded_msg = decoded_bytes.decode('utf-8')
                
                print(f"[SERVER] {username}: {decoded_msg}")
                broadcast(f"{username}: {decoded_msg}", conn)
                
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"[SERVER] Error receiving from {username}: {e}")
                break
                
    except Exception as e:
        print(f"[SERVER] Error handling client {addr}: {e}")
    
    finally:
        # Clean up when client disconnects
        if username:
            print(f"[SERVER] {username} disconnected")
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
        print(f"[SERVER] Hamming-encoded chat server started on {HOST}:{PORT}")
        print("[SERVER] This server will introduce random single-bit errors that clients will correct")
        print("[SERVER] Waiting for connections...")
        
        while True:
            try:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print("\n[SERVER] Shutting down server...")
                break
            except Exception as e:
                print(f"[SERVER] Error accepting connection: {e}")
    
    except Exception as e:
        print(f"[SERVER] Server error: {e}")
    
    finally:
        # Clean up all connections
        with clients_lock:
            for conn in list(clients.keys()):
                try:
                    conn.close()
                except:
                    pass
        server_socket.close()
        print("[SERVER] Server shut down")

if __name__ == "__main__":
    main()