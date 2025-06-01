import socket
import threading
import sys
from hamming import HammingCodec

def send_message(sock, message):
    """Send a message with Hamming encoding"""
    if not message:
        return
    
    # Encode message with Hamming code
    message_bytes = message.encode('utf-8')
    encoded_data = HammingCodec.encode_bytes(message_bytes)
    
    # Send length first, then encoded data
    length_bytes = len(encoded_data).to_bytes(4, byteorder='big')
    sock.sendall(length_bytes + encoded_data)

def receive(sock, username):
    try:
        while True:
            # Receive length first
            length_bytes = sock.recv(4)
            if len(length_bytes) != 4:
                print("\n[CLIENT] Server disconnected")
                sock.close()
                sys.exit(0)
            
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the encoded message
            encoded_data = b''
            while len(encoded_data) < message_length:
                chunk = sock.recv(message_length - len(encoded_data))
                if not chunk:
                    print("\n[CLIENT] Server disconnected")
                    sock.close()
                    sys.exit(0)
                encoded_data += chunk
            
            # Decode the Hamming-encoded message
            decoded_bytes, errors = HammingCodec.decode_bytes(encoded_data)
            
            if errors:
                print(f"\n[CLIENT] 🔧 Corrected transmission errors: {errors}")
            
            decoded_message = decoded_bytes.decode('utf-8')
            print(f"\n{decoded_message}")
            print(f"You ({username}): ", end="", flush=True)
            
    except ConnectionResetError:
        print("\n[CLIENT] Server disconnected")
    except OSError:
        # Socket was closed
        pass
    except Exception as e:
        print(f"\n[CLIENT] Error in receive: {e}")
    finally:
        print("\n[CLIENT] Disconnected from server")
        sock.close()
        sys.exit(0)

def main():
    HOST = '127.0.0.1'
    PORT = 12345
    
    username = input("Enter your username: ")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print(f"[CLIENT] Connected to Hamming-encoded chat server as {username}")
        print("[CLIENT] This client will automatically correct transmission errors using Hamming codes")
        
        # Send username to server
        send_message(s, f"USERNAME:{username}")
        
        # Start receive thread
        threading.Thread(target=receive, args=(s, username), daemon=True).start()
        
        # Main send loop
        try:
            while True:
                msg = input(f"You ({username}): ")
                if msg.lower() == 'exit':
                    print("[CLIENT] Disconnecting...")
                    break
                send_message(s, msg)
        except KeyboardInterrupt:
            print("\n[CLIENT] Disconnecting...")
        finally:
            s.close()
            sys.exit(0)
            
    except ConnectionRefusedError:
        print("[CLIENT] Could not connect to server. Is it running?")
    except Exception as e:
        print(f"[CLIENT] An error occurred: {e}")

if __name__ == "__main__":
    main()