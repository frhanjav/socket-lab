// Compile: g++ server_linux.cpp -o server_linux -lpthread -lstdc++
// Run:     ./server_linux

#include <pthread.h>   // For pthread_create, pthread_join, mutexes, etc.
#include <stdio.h>     // For printf, scanf, fgets, fprintf, etc.
#include <string.h>    // For memset, strlen, strcspn
#include <unistd.h>    // For close
#include <sys/socket.h>// For socket functions
#include <netinet/in.h>// For sockaddr_in
#include <arpa/inet.h> // For inet_ntoa (optional, for logging)
#include <errno.h>     // For errno
#include <sys/select.h>// For select
#include <signal.h>    // For signal

#include <map>         // For storing user IDs
#include <stdexcept>   // For exception handling
#include <string>      // Include C++ string
#include <vector>      // Include C++ vector
#include <algorithm>   // For std::remove with vector

// Include our RSA header
#include "rsa_chat.hpp"

#define BUFFER_SIZE 8192  // For encrypted messages

// Helper function to log crypto details (same as original)
void LogCryptoData(const std::string& received_serialized) {
    printf("\n[CRYPTO] Received binary (%zu bytes): ",
           received_serialized.size());
    for (size_t i = 0; i < received_serialized.size(); i++) {
        printf("%02X ", (unsigned char)received_serialized[i]);
        if ((i + 1) % 16 == 0 && i + 1 < received_serialized.size()) {
            printf("\n                              ");
        }
    }
    printf("\n[CRYPTO] Received string (ASCII): ");
    for (size_t i = 0; i < received_serialized.size(); i++) {
        printf("%c",
               isprint(received_serialized[i]) ? received_serialized[i] : '.');
        if ((i + 1) % 64 == 0 && i + 1 < received_serialized.size()) {
            printf("\n                              ");
        }
    }
    printf("\n");
}


// Simple lock guard class for pthread_mutex_t
class PosixMutexLock {
private:
    pthread_mutex_t& p_mutex;
public:
    PosixMutexLock(pthread_mutex_t& m) : p_mutex(m) {
        pthread_mutex_lock(&p_mutex);
    }
    ~PosixMutexLock() {
        pthread_mutex_unlock(&p_mutex);
    }
    // Prevent copying
    PosixMutexLock(const PosixMutexLock&) = delete;
    PosixMutexLock& operator=(const PosixMutexLock&) = delete;
};


// Client session structure
struct ClientSession {
    int socket; // Changed SOCKET to int
    std::vector<long long> public_key;
    pthread_t thread; // Changed HANDLE to pthread_t
    // HANDLE event; // Removed event
    std::string user_id;
    bool connected;
};

class ChatServer {
private:
    bool m_running;
    int m_server_socket; // Changed SOCKET to int
    std::vector<long long> m_server_public_key;
    std::vector<long long> m_server_private_key;
    int m_port;
    std::map<int, ClientSession> m_clients; // Keyed by socket descriptor (int)
    pthread_mutex_t m_clients_mutex; // Changed CRITICAL_SECTION to pthread_mutex_t

    struct ReceiverThreadArgs {
        ChatServer* server;
        int clientSocket; // Changed SOCKET to int
        // HANDLE hEvent; // Removed event
    };

    // Internal methods
    // bool initWinsock(); // Removed
    bool createServerSocket();
    bool bindAndListen();
    void acceptClientsLoop(); // Renamed from acceptClients for clarity
    bool exchangeKeys(int clientSocket);
    bool startClientReceiver(int clientSocket);
    void cleanupClient(int clientSocket, bool was_graceful_disconnect);
    void cleanupAllClients();
    void stopServer(); // This is the actual shutdown logic
    bool forwardMessageToClient(const std::string& recipient_id,
                                const std::string& sender_id,
                                const std::string& message,
                                int senderSocket);
    bool sendErrorToClient(int clientSocket,
                           const std::string& error_message);
    static void* clientReceiverThreadFunc(void* args_ptr); // Changed signature
    void handleReceivedMessage(int clientSocket,
                               const std::string& received_msg);

public:
    ChatServer(int port);
    ~ChatServer();
    bool initialize();
    void run();
    void shutdownServer() { stopServer(); } // Public interface to stop
};

ChatServer::ChatServer(int port)
    : m_running(false),
      m_server_socket(-1), // Changed INVALID_SOCKET to -1
      m_server_public_key({5, 323}),
      m_server_private_key({173, 323}),
      m_port(port) {
    if (pthread_mutex_init(&m_clients_mutex, NULL) != 0) {
        fprintf(stderr, "Mutex init failed. Error %d: %s\n", errno, strerror(errno));
        // Consider throwing an exception or exiting
        exit(EXIT_FAILURE);
    }
}

ChatServer::~ChatServer() {
    shutdownServer(); // Ensure server is stopped and resources released
    pthread_mutex_destroy(&m_clients_mutex);
}

// Create server socket
bool ChatServer::createServerSocket() {
    if ((m_server_socket = socket(AF_INET, SOCK_STREAM, 0)) == -1) { // Check against -1
        fprintf(stderr, "Socket creation failed. Error %d: %s\n",
                errno, strerror(errno));
        return false;
    }
    // Optional: Allow address reuse quickly after server restart
    int opt = 1;
    if (setsockopt(m_server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        fprintf(stderr, "setsockopt(SO_REUSEADDR) failed. Error %d: %s\n", errno, strerror(errno));
        // Non-fatal, but good to log
    }
    return true;
}

// Bind socket and start listening
bool ChatServer::bindAndListen() {
    struct sockaddr_in server_addr = {0};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(m_port);

    if (bind(m_server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1 ||
        listen(m_server_socket, SOMAXCONN) == -1) { // Check against -1
        fprintf(stderr, "Bind/Listen failed. Error %d: %s\n", errno, strerror(errno));
        close(m_server_socket);
        m_server_socket = -1;
        return false;
    }
    printf("Server is listening on port %d...\n", m_port);
    return true;
}

// Exchange keys with client
bool ChatServer::exchangeKeys(int clientSocket) { // Changed SOCKET to int
    char comm_buffer[BUFFER_SIZE];
    char client_user_id_c_str[256] = {0}; // C-string buffer for sscanf
    std::vector<long long> client_public_key;

    try {
        snprintf(comm_buffer, sizeof(comm_buffer), "%lld %lld",
                 m_server_public_key[0], m_server_public_key[1]);
        if (send(clientSocket, comm_buffer, strlen(comm_buffer), 0) <= 0)
            throw std::runtime_error("Send server key failed");

        memset(comm_buffer, 0, sizeof(comm_buffer));
        int key_recv_len = recv(clientSocket, comm_buffer, sizeof(comm_buffer) - 1, 0);
        if (key_recv_len <= 0) {
             if (key_recv_len == 0) throw std::runtime_error("Receive client key failed: client closed connection");
             else throw std::runtime_error("Receive client key failed");
        }
        comm_buffer[key_recv_len] = '\0';

        long long client_e, client_n;
        // Ensure sscanf reads the user ID properly
        if (sscanf(comm_buffer, "%lld %lld %255s", &client_e, &client_n, client_user_id_c_str) >= 2) {
            client_public_key = {client_e, client_n};
            std::string user_id_str = (strlen(client_user_id_c_str) > 0) ? client_user_id_c_str : "(unknown)";

            PosixMutexLock lock(m_clients_mutex);
            // Check for duplicate user ID
            for (const auto& pair : m_clients) {
                if (pair.second.connected && pair.second.user_id == user_id_str) {
                     throw std::runtime_error("User ID '" + user_id_str + "' already connected.");
                }
            }
            m_clients[clientSocket].public_key = client_public_key;
            m_clients[clientSocket].user_id = user_id_str;
            // m_clients[clientSocket].connected is set in startClientReceiver

            printf(
                "[System] Client connected: %s (Socket: %d), Key: {e=%lld, n=%lld}\n",
                user_id_str.c_str(), clientSocket,
                client_public_key[0], client_public_key[1]);
        } else {
            throw std::runtime_error("Parse client key failed");
        }
    } catch (const std::runtime_error& e) { // Catch std::runtime_error specifically
        fprintf(stderr, "[System] Key exchange error: %s (errno: %d, %s)\n",
                e.what(), errno, strerror(errno));
        // If error was duplicate user, send error message to client before closing
        if (std::string(e.what()).find("already connected") != std::string::npos) {
            std::string err_msg = "Error: User ID already in use.";
            // Temporarily use server's private key to encrypt this error as client doesn't have our pub key yet
            // This is a slight misuse, but better than nothing. Or send plain text.
            // For simplicity here, sending plain text for this specific bootstrap error.
             send(clientSocket, err_msg.c_str(), err_msg.length(), 0);
        }
        return false;
    } catch (const std::exception& e) { // Catch other general exceptions
         fprintf(stderr, "[System] Key exchange exception: %s (errno: %d, %s)\n",
                e.what(), errno, strerror(errno));
        return false;
    }
    return true;
}


void ChatServer::handleReceivedMessage(int clientSocket, const std::string& received_serialized) {
    LogCryptoData(received_serialized);

    std::vector<long long> ciphertext = deserialize_ciphertext(received_serialized);

    if (ciphertext.empty()) {
        printf(received_serialized.empty() || received_serialized == " "
                   ? "\n[Client %d]: (empty message)\n"
                   : "\n[System] Client %d sent invalid data: '%.50s'...\n",
               clientSocket, received_serialized.c_str());
        return;
    }

    std::string decrypted_message = decrypt(ciphertext, m_server_private_key);
    printf("[CRYPTO] Decrypted message from client %d: %s\n\n", clientSocket, decrypted_message.c_str());

    std::string sender_id;
    {
        PosixMutexLock lock(m_clients_mutex);
        auto it = m_clients.find(clientSocket);
        if (it != m_clients.end()) sender_id = it->second.user_id;
        else sender_id = "UnknownClient(" + std::to_string(clientSocket) + ")";
    }
    
    if (decrypted_message == "exit") {
        printf("[System] Client %s (%d) sent exit command.\n", sender_id.c_str(), clientSocket);
        // The client's receiver thread will detect the socket closure or send failure
        // and call cleanupClient. No explicit action here other than logging.
        // cleanupClient(clientSocket, true); // This might be called too early if client hasn't shut down send side
        return;
    }


    size_t separator_pos = decrypted_message.find('/');
    if (separator_pos != std::string::npos) {
        std::string recipient_id = decrypted_message.substr(0, separator_pos);
        std::string message_content = decrypted_message.substr(separator_pos + 1);

        // Basic trim (can be more robust)
        recipient_id.erase(0, recipient_id.find_first_not_of(" \t\r\n"));
        recipient_id.erase(recipient_id.find_last_not_of(" \t\r\n") + 1);

        printf("\n[%s→%s]: %s\n", sender_id.c_str(), recipient_id.c_str(), message_content.c_str());

        if (!forwardMessageToClient(recipient_id, sender_id, message_content, clientSocket)) {
             printf("[System] Failed to forward to %s or user not found.\n", recipient_id.c_str());
             // Error message is sent by forwardMessageToClient or its callee sendErrorToClient
        } else {
            printf("[System] Message forwarded from %s to %s.\n", sender_id.c_str(), recipient_id.c_str());
        }

    } else {
        printf("\n[%s]: %s (Broadcast not implemented, message dropped or treat as error)\n", sender_id.c_str(), decrypted_message.c_str());
        // sendErrorToClient(clientSocket, "Server received: " + decrypted_message + " (Broadcast not supported, use userID/message)");
    }
}

bool ChatServer::forwardMessageToClient(const std::string& recipient_id, const std::string& sender_id,
                                        const std::string& message, int senderSocket) {
    int recipient_socket = -1;
    std::vector<long long> recipient_public_key;
    bool found = false;
    {
        PosixMutexLock lock(m_clients_mutex);
        for (const auto& client_pair : m_clients) {
            if (client_pair.second.user_id == recipient_id && client_pair.second.connected) {
                recipient_socket = client_pair.first;
                recipient_public_key = client_pair.second.public_key;
                found = true;
                break;
            }
        }
    }

    if (!found || recipient_socket == -1 || recipient_public_key.empty()) {
        sendErrorToClient(senderSocket, "Error: User '" + recipient_id + "' not found or not connected.");
        return false;
    }

    std::string formatted_message = "[DM from " + sender_id + "]: " + message;
    std::vector<long long> ciphertext = encrypt(formatted_message, recipient_public_key);
    std::string serialized_ciphertext = serialize_ciphertext(ciphertext);

    if (send(recipient_socket, serialized_ciphertext.c_str(), serialized_ciphertext.length(), 0) <= 0) {
        fprintf(stderr, "[System] Send to %s (%d) failed. Error %d: %s\n",
                recipient_id.c_str(), recipient_socket, errno, strerror(errno));
        // Recipient might have disconnected, their thread will handle cleanup.
        sendErrorToClient(senderSocket, "Error: Failed to deliver message to '" + recipient_id + "'. They may have disconnected.");
        return false;
    }
    return true;
}

bool ChatServer::sendErrorToClient(int clientSocket, const std::string& error_message) {
    std::vector<long long> client_public_key;
    bool client_exists_and_connected = false;
    {
        PosixMutexLock lock(m_clients_mutex);
        auto it = m_clients.find(clientSocket);
        if (it != m_clients.end() && it->second.connected) {
            client_public_key = it->second.public_key;
            client_exists_and_connected = true;
        }
    }

    if (!client_exists_and_connected || client_public_key.empty()) {
        fprintf(stderr, "[System] Cannot send error to client %d: not found, not connected, or no public key.\n", clientSocket);
        return false;
    }

    std::vector<long long> ciphertext = encrypt(error_message, client_public_key);
    std::string serialized_ciphertext = serialize_ciphertext(ciphertext);

    if (send(clientSocket, serialized_ciphertext.c_str(), serialized_ciphertext.length(), 0) <= 0) {
        fprintf(stderr, "[System] Failed to send error message to client %d. Error %d: %s\n",
                clientSocket, errno, strerror(errno));
        return false;
    }
    return true;
}


void* ChatServer::clientReceiverThreadFunc(void* args_ptr) { // Changed signature
    ReceiverThreadArgs* thread_args = (ReceiverThreadArgs*)args_ptr;
    ChatServer* server = thread_args->server;
    int clientSocket = thread_args->clientSocket;

    char recv_buffer[BUFFER_SIZE];
    int recv_len;
    std::string user_id = "Unknown";
    bool graceful_disconnect = false;
    {
        PosixMutexLock lock(server->m_clients_mutex);
        auto it = server->m_clients.find(clientSocket);
        if (it != server->m_clients.end()) {
            user_id = it->second.user_id;
        }
    }

    printf("[Receiver] Thread started for client %s (Socket %d).\n", user_id.c_str(), clientSocket);

    while (server->m_running) { // Check global server running flag
        memset(recv_buffer, 0, BUFFER_SIZE);
        recv_len = recv(clientSocket, recv_buffer, BUFFER_SIZE - 1, 0);

        if (recv_len > 0) {
            recv_buffer[recv_len] = '\0';
            std::string received_serialized(recv_buffer);
            server->handleReceivedMessage(clientSocket, received_serialized);
        } else if (recv_len == 0) {
            printf("\n[System] Client %s (%d) disconnected gracefully.\n", user_id.c_str(), clientSocket);
            graceful_disconnect = true;
            break;
        } else { // recv_len < 0
            int error_code = errno;
             // Check if the client is still marked as connected before printing error
            bool still_marked_connected = false;
            {
                PosixMutexLock lock(server->m_clients_mutex);
                auto it = server->m_clients.find(clientSocket);
                if (it != server->m_clients.end()) {
                    still_marked_connected = it->second.connected;
                }
            }
            if(still_marked_connected) { // Avoid redundant messages if already being cleaned up
                 printf("\n[System] recv failed for %s (%d) (Error: %d - %s). Connection lost.\n",
                       user_id.c_str(), clientSocket, error_code, strerror(error_code));
            }
            break;
        }
    }

    printf("[Receiver] Thread for client %s (%d) exiting.\n", user_id.c_str(), clientSocket);
    server->cleanupClient(clientSocket, graceful_disconnect); // Perform cleanup
    delete thread_args;
    pthread_exit(NULL);
    return NULL;
}

bool ChatServer::startClientReceiver(int clientSocket) { // Changed SOCKET to int
    ReceiverThreadArgs* args = new ReceiverThreadArgs();
    if (!args) {
        fprintf(stderr, "[System] Thread resource allocation failed.\n");
        return false;
    }
    args->server = this;
    args->clientSocket = clientSocket;

    pthread_t client_thread_id;
    if (pthread_create(&client_thread_id, NULL, &clientReceiverThreadFunc, args) != 0) {
        fprintf(stderr,
                "[System] Receiver thread creation failed for socket %d. (Error: %d - %s)\n",
                clientSocket, errno, strerror(errno));
        delete args;
        return false;
    }

    PosixMutexLock lock(m_clients_mutex);
    auto it = m_clients.find(clientSocket);
    if (it != m_clients.end()) {
        it->second.thread = client_thread_id;
        it->second.connected = true; // Mark as fully connected now
         // Announce new user to existing users (optional feature)
    } else {
        // This should not happen if clientSocket was added to m_clients before calling this
        fprintf(stderr, "[System] CRITICAL: Client socket %d not found in map during thread start.\n", clientSocket);
        // Detach or join the created thread to clean it up if we can't store it
        pthread_detach(client_thread_id); // or attempt to join with a timeout
        delete args;
        return false;
    }
    return true;
}

void ChatServer::acceptClientsLoop() {
    fd_set read_fds;
    struct timeval tv;

    printf("[System] Server running. Press Ctrl+C to shut down.\n");

    while (m_running) {
        FD_ZERO(&read_fds);
        FD_SET(m_server_socket, &read_fds);

        tv.tv_sec = 1;
        tv.tv_usec = 0;

        // The first argument to select should be the highest fd + 1.
        // Here, we are only listening on m_server_socket.
        int activity = select(m_server_socket + 1, &read_fds, NULL, NULL, &tv);

        if (!m_running) break; // Check again after select returns

        if (activity < 0) { // SOCKET_ERROR is -1
            if (errno == EINTR) continue; // Interrupted by a signal, try again
            fprintf(stderr, "[System] Select failed. Error %d: %s\n", errno, strerror(errno));
            m_running = false; // Stop server on select error
            break;
        }

        if (activity > 0 && FD_ISSET(m_server_socket, &read_fds)) {
            struct sockaddr_in client_addr_info;
            socklen_t client_addr_len = sizeof(client_addr_info); // socklen_t for POSIX

            int new_client_socket = accept(m_server_socket, (struct sockaddr*)&client_addr_info, &client_addr_len);

            if (new_client_socket == -1) { // INVALID_SOCKET is -1
                fprintf(stderr, "[System] Accept failed. Error %d: %s\n", errno, strerror(errno));
                continue;
            }
            
            printf("[System] New client connection accepted from %s:%d (Socket: %d).\n",
                    inet_ntoa(client_addr_info.sin_addr), ntohs(client_addr_info.sin_port), new_client_socket);


            // Initialize client session structure before lock
            ClientSession new_session = {
                new_client_socket, {}, 0, "", false // socket, pub_key, thread, user_id, connected
            };
            {
                PosixMutexLock lock(m_clients_mutex);
                m_clients[new_client_socket] = new_session;
            }


            if (exchangeKeys(new_client_socket)) {
                if (!startClientReceiver(new_client_socket)) {
                    fprintf(stderr, "[System] Failed to start client thread for socket %d.\n", new_client_socket);
                    cleanupClient(new_client_socket, false); // Clean up partially initialized client
                } else {
                    printf("[System] Client session started successfully for socket %d.\n", new_client_socket);
                }
            } else {
                fprintf(stderr, "[System] Key exchange failed with client on socket %d.\n", new_client_socket);
                cleanupClient(new_client_socket, false); // Clean up client after failed key exchange
            }
        }
    }
}


void ChatServer::cleanupClient(int clientSocket, bool was_graceful_disconnect) {
    pthread_t client_thread_id = 0;
    std::string user_id_to_clean;
    bool actually_remove = false;

    {
        PosixMutexLock lock(m_clients_mutex);
        auto it = m_clients.find(clientSocket);
        if (it != m_clients.end()) {
            if (it->second.connected || !was_graceful_disconnect) { // Only log/cleanup if was connected or error
                 user_id_to_clean = it->second.user_id.empty() ? ("Socket " + std::to_string(clientSocket)) : it->second.user_id;
            }
            
            client_thread_id = it->second.thread; // Get thread ID for joining, if it exists
            it->second.connected = false; // Mark as disconnected

            // Actual removal from map and socket closing happens after releasing lock if thread join is needed
            // or directly if no thread to join (e.g., failed before thread start)
            if (clientSocket != -1) {
                 shutdown(clientSocket, SHUT_RDWR); // Changed SD_BOTH to SHUT_RDWR
                 close(clientSocket);
            }
            m_clients.erase(it); // Remove from map
            actually_remove = true; // Flag that we proceeded with removal logic
        }
    } // Mutex released

    if (client_thread_id != 0) {
        // Don't join if current thread is the one being cleaned up (shouldn't happen here, but good practice)
        if (pthread_self() != client_thread_id) {
             printf("[System] Waiting for client thread for %s (%d) to finish...\n", user_id_to_clean.c_str(), clientSocket);
             pthread_join(client_thread_id, NULL); // Wait for the thread to exit
        } else {
             // This case should ideally not happen where a thread tries to join itself.
             // If it does, detach it to allow resources to be freed upon exit.
             pthread_detach(client_thread_id);
        }
    }
    
    if (actually_remove && !user_id_to_clean.empty()) {
        printf("[System] Client %s disconnected and cleaned up.\n", user_id_to_clean.c_str());

        PosixMutexLock lock(m_clients_mutex);
        printf("[System] Remaining connected users: ");
        bool any_left = false;
        for (const auto& client_pair : m_clients) {
            if (client_pair.second.connected) {
                printf("%s ", client_pair.second.user_id.c_str());
                any_left = true;
            }
        }
        if (!any_left) {
            printf("none");
        }
        printf("\n");
    }
}


void ChatServer::cleanupAllClients() {
    std::vector<int> client_sockets_to_clean;
    {
        PosixMutexLock lock(m_clients_mutex);
        for (auto const& client_pair : m_clients) {
            client_sockets_to_clean.push_back(client_pair.first);
        }
    }

    printf("[System] Cleaning up %zu clients...\n", client_sockets_to_clean.size());
    for (int sock : client_sockets_to_clean) {
        // The client's own thread usually calls cleanupClient.
        // This is more of a forceful cleanup if server is shutting down.
        // Mark as not graceful if server initiated.
        cleanupClient(sock, false);
    }
    m_clients.clear(); // Should be empty if cleanupClient worked correctly
}

void ChatServer::stopServer() {
    if (!m_running) return; // Already stopped or stopping

    m_running = false; // Signal all loops to stop
    printf("[System] Shutting down server...\n");

    // Close the server socket to prevent new connections
    // This will also cause acceptClientsLoop's select to unblock (or error out)
    if (m_server_socket != -1) {
        //shutdown(m_server_socket, SHUT_RDWR); // Not strictly necessary for listening socket
        close(m_server_socket);
        m_server_socket = -1;
    }
    
    cleanupAllClients(); // This will join all client threads

    // WSACleanup(); // Removed
    printf("[System] Server shut down complete.\n");
}

bool ChatServer::initialize() {
    // if (!initWinsock() || ... ) // Removed initWinsock
    if (!createServerSocket() || !bindAndListen()) {
        if (m_server_socket != -1) close(m_server_socket);
        return false;
    }
    m_running = true;
    return true;
}

void ChatServer::run() {
    if (!m_running) {
        fprintf(stderr, "[System] Server not initialized properly.\n");
        return;
    }
    acceptClientsLoop(); // Start accepting clients
    // When acceptClientsLoop exits (because m_running is false), stopServer will do final cleanup.
    // However, stopServer might have already been called by a signal handler or another thread.
    // The m_running flag and checks in stopServer handle this.
    if (m_server_socket != -1) { // If server socket is still open, means loop exited due to m_running
        stopServer(); // Ensure full cleanup if not initiated by explicit shutdownServer call
    }
}


ChatServer* g_server_ptr = nullptr; // Global pointer for signal handler

void handle_sigint(int sig) {
    printf("\n[System] SIGINT received. Shutting down server...\n");
    if (g_server_ptr) {
        g_server_ptr->shutdownServer(); // Call the graceful shutdown
    }
    // If you want to ensure main exits after this:
    // exit(0); // Or let main return naturally
}


int main() {
    // Ignore SIGPIPE, so send() failures are handled by return codes
    signal(SIGPIPE, SIG_IGN);
    // Handle Ctrl+C (SIGINT) for graceful shutdown
    signal(SIGINT, handle_sigint);


    int port;
    printf("Enter port number to host on (e.g., 8080): ");
    if (scanf("%d", &port) != 1 || port <= 0 || port > 65535) {
        fprintf(stderr, "Invalid port. Please enter a number between 1 and 65535.\n");
        return 1;
    }

    int c; // Clear stdin buffer after scanf
    while ((c = getchar()) != '\n' && c != EOF);


    ChatServer server(port);
    g_server_ptr = &server; // Set global pointer for signal handler

    if (!server.initialize()) {
        fprintf(stderr, "Server initialization failed.\n");
        g_server_ptr = nullptr;
        return 1;
    }

    server.run(); // This will block until m_running is false

    g_server_ptr = nullptr;
    printf("[System] Server main function finished.\n");
    return 0;
}