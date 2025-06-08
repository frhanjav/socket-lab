# server.py
import socket
import threading
import random
import logging # Using standard logging for server output


HOST = '0.0.0.0'
PORT = 5000

SINGLE_BIT_ERROR_PROBABILITY = 0.5
DOUBLE_BIT_ERROR_PROBABILITY = 0.3

clients = {}
lock = threading.Lock()

# Configure basic logging for the server
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SERVER] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClientHandler(threading.Thread):
    def __init__(self, conn: socket.socket, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.user_id = None

    def introduce_bit_errors(self, hamming_data):
        if not hamming_data: # Check for empty string
            return hamming_data, {'errors_introduced': False, 'error_type': None, 'positions': []}
        
        data_list = list(hamming_data)
        error_info = {'errors_introduced': False, 'error_type': None, 'positions': []}
        
        # Ensure there are enough bits for double error if selected
        can_double_error = len(data_list) >= 2
        
        rand_val = random.random()

        if rand_val < DOUBLE_BIT_ERROR_PROBABILITY and can_double_error:
            positions_0_indexed = random.sample(range(len(data_list)), 2)
            for pos_0_indexed in positions_0_indexed:
                data_list[pos_0_indexed] = '1' if data_list[pos_0_indexed] == '0' else '0'
            error_info = {
                'errors_introduced': True,
                'error_type': 'double',
                'positions': [p + 1 for p in positions_0_indexed] # 1-indexed
            }
        elif rand_val < (DOUBLE_BIT_ERROR_PROBABILITY + SINGLE_BIT_ERROR_PROBABILITY) and len(data_list) > 0:
            # This ensures probabilities are somewhat independent if DOUBLE_BIT_ERROR_PROBABILITY is high
            # A better way might be to check for double, then if not, check for single based on its own prob.
            # Let's adjust:
            # Roll for double. If not, then roll for single.
            # This logic is kept from original, but could be improved if precise independent probabilities are needed.
            # Current logic: if rand < D_PROB -> double. elif rand < D_PROB + S_PROB -> single.
            # This means S_PROB is conditional on not D_PROB occurring *within that range*.

            pos_0_indexed = random.randint(0, len(data_list) - 1)
            data_list[pos_0_indexed] = '1' if data_list[pos_0_indexed] == '0' else '0'
            error_info = {
                'errors_introduced': True,
                'error_type': 'single',
                'positions': [pos_0_indexed + 1] # 1-indexed
            }
        
        return ''.join(data_list), error_info

    def run(self) -> None:
        try:
            prompt_msg = "Enter your user ID:\n" # Server asks client
            self.conn.sendall(prompt_msg.encode('utf-8'))
            
            user_id_data = self.conn.recv(1024)
            if not user_id_data: # Connection closed before sending user ID
                logger.info(f"Connection from {self.addr} closed before user ID was sent.")
                return
            self.user_id = user_id_data.decode('utf-8').strip()

            if not self.user_id: # Empty user ID
                logger.warning(f"Client from {self.addr} provided an empty user ID. Closing connection.")
                self.conn.sendall("SERVER_ERROR|User ID cannot be empty.".encode('utf-8'))
                return

            with lock:
                if self.user_id in clients:
                    logger.warning(f"User ID '{self.user_id}' already connected. Closing new connection from {self.addr}.")
                    self.conn.sendall(f"SERVER_ERROR|User ID '{self.user_id}' is already in use.".encode('utf-8'))
                    return # Important to return here, otherwise it proceeds
                clients[self.user_id] = self.conn
            
            logger.info(f"{self.user_id} connected from {self.addr}")

            while True:
                raw_data = self.conn.recv(4096)
                if not raw_data:
                    break 
                
                try:
                    msg_text = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    logger.error(f"Unicode decode error from {self.user_id}")
                    # Optionally notify client, but might be tricky if their side also has issues
                    continue

                parts = msg_text.split('|', 2)
                if len(parts) != 3:
                    logger.error(f"Invalid message format from {self.user_id}: {msg_text}")
                    self.conn.sendall("SERVER_ERROR|Invalid message format. Use recipient|original_message|hamming_payload".encode('utf-8'))
                    continue
                
                recipient, original_msg, hamming_payload = parts
                
                logger.info(f"Forwarding from {self.user_id} → {recipient} (Original: '{original_msg}')")
                
                corrupted_hamming, error_info = self.introduce_bit_errors(hamming_payload)
                
                if error_info['errors_introduced']:
                    if error_info['error_type'] == 'single':
                        logger.warning(f"🔴 Introduced SINGLE bit error at position {error_info['positions'][0]} for message to {recipient}")
                    else: 
                        logger.warning(f"🔴🔴 Introduced DOUBLE bit errors at positions {error_info['positions']} for message to {recipient}")
                else:
                    logger.info(f"✅ Clean transmission (no errors introduced) for message to {recipient}")

                with lock:
                    target_conn = clients.get(recipient)
                
                if target_conn:
                    forward_payload = f"{original_msg}|{corrupted_hamming}"
                    try:
                        target_conn.sendall(forward_payload.encode('utf-8'))
                        logger.info(f"✉️ Message from {self.user_id} delivered to {recipient}")
                    except socket.error as e:
                        logger.error(f"Socket error sending to {recipient}: {e}. Removing client.")
                        # Assume client disconnected, remove them
                        with lock:
                            clients.pop(recipient, None)
                        # Notify sender if possible, or just log
                        self.conn.sendall(f"SERVER_ERROR|Failed to send message to '{recipient}', they might have disconnected.".encode('utf-8'))
                else:
                    logger.warning(f"❌ Recipient {recipient} not found or offline for message from {self.user_id}")
                    self.conn.sendall(f"SERVER_ERROR|User '{recipient}' not found or offline.".encode('utf-8'))
                    
        except ConnectionResetError:
            logger.info(f"Client {self.user_id or self.addr} disconnected abruptly.")
        except Exception as e:
            logger.error(f"Error handling client {self.user_id or self.addr}: {e}", exc_info=True) # exc_info for traceback
        finally:
            with lock:
                if self.user_id and self.user_id in clients:
                    clients.pop(self.user_id, None)
            if self.conn:
                self.conn.close()
            logger.info(f"{self.user_id or 'Unknown client from ' + str(self.addr)} disconnected.")


def start_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        logger.info(f"Hamming Chat Server listening on {HOST}:{PORT}...")
        logger.info("Error Simulation Settings:")
        logger.info(f"  • Single bit error probability: {SINGLE_BIT_ERROR_PROBABILITY:.1%}")
        logger.info(f"  • Double bit error probability: {DOUBLE_BIT_ERROR_PROBABILITY:.1%}")
        logger.info("Server ready - forwarding messages with potential bit errors.")
        
        try:
            while True:
                conn, addr = s.accept()
                logger.info(f"New connection from {addr}")
                ClientHandler(conn, addr).start()
        except KeyboardInterrupt:
            logger.info("Server shutting down due to KeyboardInterrupt...")
        except Exception as e:
            logger.critical(f"Server encountered a critical error: {e}", exc_info=True)
        finally:
            logger.info("Server has shut down.")

if __name__ == '__main__':
    start_server()