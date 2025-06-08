# client.py
import socket
import threading
import logging
from hamming_utils import HammingCode

HOST = '127.0.0.1'
PORT = 5000

hamming = HammingCode()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client_hamming.log')
    ]
)

def receive(sock: socket.socket, user_id: str) -> None:
    try:
        while True:
            raw_data = sock.recv(4096)
            if not raw_data:
                print("\n[CLIENT] Connection closed by server.")
                break
            
            raw = raw_data.decode('utf-8')
            
            if raw.startswith("SERVER_ERROR|"):
                error_content = raw.split("|", 1)[1]
                print(f"\n[SERVER ERROR] {error_content}")
                # No longer re-printing prompt from here, main input loop handles it
                continue
            
            parts = raw.split('|', 1)
            if len(parts) != 2:
                print("\n[CLIENT] Invalid message format received from server.")
                continue
            
            original_msg, hamming_payload = parts
            
            try:
                decoded_msg, error_info = hamming.decode(hamming_payload)
                
                if not error_info['repairable']:
                    print("\n--- [TRANSMISSION ERROR] ---")
                    print("Non-repairable transmission error detected!")
                    print("Message corrupted and cannot be recovered.")
                    print("----------------------------")
                    continue
                
                # Display the message
                if error_info['error_detected'] and error_info['error_corrected']:
                    print(f"\n--- [MESSAGE (Error Corrected at bit {error_info['error_position']})] ---")
                    print(f"{decoded_msg}")
                    print("--------------------------------------------------")
                else:
                    print("\n--- [MESSAGE] ---")
                    print(f"{decoded_msg}")
                    print("-----------------")
                
                # Verify message integrity by comparing with original
                if decoded_msg != original_msg:
                    print(f"[WARNING] Decoded message '{decoded_msg}' differs from original transmission '{original_msg}'!")
                
            except Exception as e:
                print(f"\n[CLIENT] Error decoding message: {e}")
            
            # The input prompt is handled by the main loop's input()
            # No need to print "You: " here explicitly after each message
            # as it might interfere with user typing.
            # A simple newline can help separate messages from the input prompt area visually.
            print() # Adds a little space before the next potential prompt from main loop
            
    except ConnectionResetError:
        print("\n[CLIENT] Connection lost to server.")
    except UnicodeDecodeError:
        print("\n[CLIENT] Received non-UTF-8 data from server.")
    except Exception as e:
        print(f"\n[CLIENT] Receive error: {e}")
    finally:
        print("\n[CLIENT] Receive thread terminated.")


def start_client() -> None:
    """Start the Hamming chat client"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            
            print("\n--- [HAMMING CHAT] ---")
            print("Welcome to Hamming Chat Client!")
            print("Error detection and correction enabled.")
            print("----------------------")
            
            server_prompt_data = s.recv(1024)
            server_prompt = server_prompt_data.decode('utf-8').strip()
            # print(f"[SERVER] {server_prompt}") # Optional: display server's prompt text
            
            user_id = input("Enter your user ID: ")
            s.sendall(user_id.encode('utf-8'))
            
            threading.Thread(target=receive, args=(s, user_id), daemon=True).start()
            
            print("\n--- [INSTRUCTIONS] ---")
            print("Usage: recipient_id/Your message here")
            print("Type '/quit' to exit")
            print("--------------------")
            
            while True:
                try:
                    # Prompt for input. Received messages will print above this line.
                    text = input(f"[{user_id}] You: ")
                    
                    if text.lower() == '/quit':
                        print("Disconnecting...")
                        break
                    
                    if '/' not in text:
                        print("Invalid format! Use: recipient_id/message")
                        continue
                    
                    recipient, message = text.split('/', 1)
                    
                    if not recipient.strip() or not message.strip():
                        print("Both recipient and message are required!")
                        continue
                    
                    try:
                        hamming_encoded = hamming.encode(message)
                        payload = f"{recipient.strip()}|{message}|{hamming_encoded}"
                        s.sendall(payload.encode('utf-8'))
                        print(f"Message sent to {recipient} ({len(hamming_encoded)} bits encoded).")
                    except Exception as e:
                        print(f"Encoding error: {e}")
                
                except KeyboardInterrupt:
                    print("\nCaught KeyboardInterrupt, quitting...")
                    break
                except EOFError: # Handle Ctrl+D
                    print("\nEOFError, quitting...")
                    break
                except Exception as e:
                    print(f"Input error: {e}")
    
    except ConnectionRefusedError:
        print("\n--- [CONNECTION ERROR] ---")
        print(f"Cannot connect to server at {HOST}:{PORT}")
        print("Make sure the server is running!")
        print("--------------------------")
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        print("Goodbye! Hamming Chat Client closed.")


if __name__ == '__main__':
    start_client()