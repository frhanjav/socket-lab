// Compile: g++ client_linux.cpp -o client_linux -lpthread -lstdc++
// Run:     ./client_linux

#include <pthread.h>   // For pthread_create, pthread_join, etc.
#include <stdio.h>     // For printf, scanf, fgets, fprintf, etc.
#include <string.h>    // For memset, strlen, strcspn, strcpy
#include <unistd.h>    // For close
#include <sys/socket.h>// For socket functions
#include <netinet/in.h>// For sockaddr_in
#include <arpa/inet.h> // For inet_addr
#include <errno.h>     // For errno
#include <signal.h>    // For signal

#include <stdexcept>   // For exception handling
#include <string>      // Include C++ string
#include <vector>      // Include C++ vector

// Include our RSA header
#include "rsa_chat.hpp"

#define DEFAULT_PORT 8080
#define DEFAULT_IP "127.0.0.1"
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

class ChatClient {
private:
    bool m_connection_active;
    int m_sock; // Changed SOCKET to int
    std::vector<long long> m_client_public_key;
    std::vector<long long> m_client_private_key;
    std::vector<long long> m_server_public_key;
    pthread_t m_recv_thread; // Changed HANDLE to pthread_t

    struct ReceiverThreadArgs {
        ChatClient* client;
        // HANDLE hEvent; // Removed event, join will be used
    };

    // Internal methods
    // bool initWinsock(); // Removed
    bool createSocket();
    bool connectToServer(const char* ip, int port);
    bool exchangeKeys_userID(const char* user_id);
    bool startReceiver();
    void messageLoop();
    void cleanup();

    // Thread receiver function
    static void* receiverThreadFunc(void* args_ptr); // Changed signature
    void handleReceivedMessage(const std::string& received_msg);

public:
    ChatClient();
    ~ChatClient();
    bool initialize(const char* server_ip, int server_port,
                    const char* user_id);
    bool run();
};

ChatClient::ChatClient()
    : m_connection_active(false),
      m_sock(-1), // Changed INVALID_SOCKET to -1
      m_client_public_key({7, 299}),
      m_client_private_key({151, 299}),
      m_recv_thread(0) {} // Initialize pthread_t to 0 or similar

ChatClient::~ChatClient() { cleanup(); }

// Create socket
bool ChatClient::createSocket() {
    if ((m_sock = socket(AF_INET, SOCK_STREAM, 0)) == -1) { // Check against -1
        fprintf(stderr, "Socket creation failed. Error %d: %s\n",
                errno, strerror(errno));
        return false;
    }
    return true;
}

// Connect to server
bool ChatClient::connectToServer(const char* ip, int port) {
    struct sockaddr_in server_addr = {0};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);

    // inet_pton is more modern, but inet_addr is POSIX and simpler for IPv4
    if (inet_aton(ip, &server_addr.sin_addr) == 0) { // inet_aton returns 0 on error
        fprintf(stderr, "Invalid server IP address provided: %s\n", ip);
        // inet_addr could also be used:
        // server_addr.sin_addr.s_addr = inet_addr(ip);
        // if (server_addr.sin_addr.s_addr == INADDR_NONE) {
        //     fprintf(stderr, "Invalid server IP address provided.\n");
        //     return false;
        // }
        return false;
    }


    printf("Connecting to %s:%d...\n", ip, port);
    if (connect(m_sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        fprintf(stderr, "Connect failed. Error %d: %s\n", errno, strerror(errno));
        return false;
    }

    printf("[System] Connected. Performing key exchange...\n");
    return true;
}

// Exchange keys with server
bool ChatClient::exchangeKeys_userID(const char* user_id) {
    char comm_buffer[BUFFER_SIZE];
    m_server_public_key.clear();

    try {
        memset(comm_buffer, 0, sizeof(comm_buffer));
        int key_recv_len = recv(m_sock, comm_buffer, sizeof(comm_buffer) - 1, 0);
        if (key_recv_len <= 0) {
            if (key_recv_len == 0) throw std::runtime_error("Receive server key failed: server closed connection");
            else throw std::runtime_error("Receive server key failed"); // errno will be set
        }
        comm_buffer[key_recv_len] = '\0';

        long long server_e, server_n;
        if (sscanf(comm_buffer, "%lld %lld", &server_e, &server_n) == 2) {
            m_server_public_key.assign({server_e, server_n});
            printf("[System] Server public key received: {e=%lld, n=%lld}\n",
                   m_server_public_key[0], m_server_public_key[1]);
        } else {
            throw std::runtime_error("Parse server key failed");
        }

        snprintf(comm_buffer, sizeof(comm_buffer), "%lld %lld %s",
                 m_client_public_key[0], m_client_public_key[1], user_id);
        if (send(m_sock, comm_buffer, strlen(comm_buffer), 0) <= 0) {
            throw std::runtime_error("Send client key failed"); // errno will be set
        }

    } catch (const std::exception& e) {
        fprintf(stderr, "[System] Key exchange error: %s. (errno: %d, %s)\n",
                e.what(), errno, strerror(errno));
        return false;
    }

    printf("[System] Key exchange successful. Chat session started.\n");
    return true;
}

// Handle received messages
void ChatClient::handleReceivedMessage(const std::string& received_serialized) {
    LogCryptoData(received_serialized);

    std::vector<long long> ciphertext = deserialize_ciphertext(received_serialized);

    if (ciphertext.empty()) {
        if (received_serialized.empty() || received_serialized == " ") {
            printf("[Server]: (empty message)\n> ");
        } else {
            printf("[System] Received invalid data: '%.50s'...\n> ",
                   received_serialized.c_str());
        }
        fflush(stdout); // Ensure prompt is displayed
        return;
    }

    std::string decrypted_message = decrypt(ciphertext, m_client_private_key);
    printf("[CRYPTO] Decrypted message: %s\n\n", decrypted_message.c_str());
    printf("[Server]: %s\n> ", decrypted_message.c_str());
    fflush(stdout); // Ensure prompt is displayed
}

// Receiver thread function
void* ChatClient::receiverThreadFunc(void* args_ptr) { // Changed signature
    ReceiverThreadArgs* thread_args = (ReceiverThreadArgs*)args_ptr;
    ChatClient* client = thread_args->client;

    char recv_buffer[BUFFER_SIZE];
    int recv_len;

    printf("[Receiver] Thread started.\n");
    while (client->m_connection_active) {
        memset(recv_buffer, 0, BUFFER_SIZE);
        recv_len = recv(client->m_sock, recv_buffer, BUFFER_SIZE - 1, 0);

        if (recv_len > 0) {
            recv_buffer[recv_len] = '\0';
            std::string received_serialized(recv_buffer);
            client->handleReceivedMessage(received_serialized);
        } else if (recv_len == 0) {
            printf("\n[System] Server disconnected.\n> ");
            fflush(stdout);
            client->m_connection_active = false;
            break;
        } else {  // recv_len < 0
            int error_code = errno;
            if (client->m_connection_active) { // Check if still active to avoid double message on cleanup
                printf(
                    "\n[System] recv failed (Error: %d - %s). Connection lost.\n> ",
                    error_code, strerror(error_code));
                fflush(stdout);
                client->m_connection_active = false;
            }
            break;
        }
    }

    printf("[Receiver] Thread exiting.\n");
    delete thread_args;
    pthread_exit(NULL); // Use pthread_exit
    return NULL; // Keep compiler happy
}

// Start receiver thread
bool ChatClient::startReceiver() {
    ReceiverThreadArgs* args = new ReceiverThreadArgs();
    if (!args) {
        fprintf(stderr, "[System] Thread resource allocation failed.\n");
        return false;
    }
    args->client = this;

    if (pthread_create(&m_recv_thread, NULL, &receiverThreadFunc, args) != 0) {
        fprintf(stderr,
                "[System] Receiver thread creation failed. (Error: %d - %s)\n",
                errno, strerror(errno));
        delete args;
        return false;
    }
    return true;
}

// Main message loop
void ChatClient::messageLoop() {
    char comm_buffer[BUFFER_SIZE];
    printf("Chat commands:\n");
    printf("- Direct message: userID/your message here\n");
    printf("- Exit: exit\n");
    printf("> ");
    fflush(stdout);

    while (m_connection_active) {
        if (fgets(comm_buffer, sizeof(comm_buffer), stdin) != NULL) {
            comm_buffer[strcspn(comm_buffer, "\n")] = 0;
            std::string plaintext_message(comm_buffer);

            if (!m_connection_active) break; // Check again after blocking fgets

            if (m_server_public_key.empty()) {
                printf(
                    "[System] Server public key not available. Cannot send.\n> ");
                fflush(stdout);
                continue;
            }

            std::vector<long long> ciphertext =
                encrypt(plaintext_message, m_server_public_key);
            std::string serialized_ciphertext =
                serialize_ciphertext(ciphertext);

            if (send(m_sock, serialized_ciphertext.c_str(),
                     serialized_ciphertext.length(), 0) <= 0) {
                if (m_connection_active) {
                    fprintf(stderr, "[System] send failed. Error %d: %s\n",
                            errno, strerror(errno));
                    m_connection_active = false; // Trigger loop exit and cleanup
                }
                break;
            }

            if (plaintext_message == "exit") {
                printf("[System] Disconnecting...\n");
                m_connection_active = false; // Signal receiver thread to stop
                break;
            }
            printf("> ");
            fflush(stdout);
        } else {
            // fgets failed (e.g. EOF on stdin)
            if (feof(stdin)) {
                printf("\n[System] Input stream closed (EOF). Disconnecting...\n");
            } else {
                printf("\n[System] Console input error. Disconnecting...\n");
            }
            m_connection_active = false;
            break;
        }
    }
}

// Clean up resources
void ChatClient::cleanup() {
    bool was_active = m_connection_active;
    m_connection_active = false; // Ensure threads know to stop

    if (m_sock != -1) {
        if (was_active) { // Only shutdown if connection was thought to be active
            // Shutdown sending side to signal server, if not already done by "exit"
            // This helps the receiver thread to unblock if it's in a recv() call
            // and the server hasn't disconnected yet.
            shutdown(m_sock, SHUT_WR); // Changed SD_SEND to SHUT_WR
        }
    }

    if (m_recv_thread != 0) {
        printf("[System] Waiting for receiver thread to finish...\n");
        pthread_join(m_recv_thread, NULL); // Wait for thread to complete
        m_recv_thread = 0;
    }

    if (m_sock != -1) {
        close(m_sock); // Changed closesocket to close
        m_sock = -1;
    }
    // WSACleanup(); // Removed
    printf("[System] Client cleanup complete.\n");
}

// Initialize the client
bool ChatClient::initialize(const char* server_ip, int server_port, const char* user_id) {
    // if (!initWinsock() || !createSocket() || ... ) // Removed initWinsock
    if (!createSocket() || !connectToServer(server_ip, server_port)) {
        cleanup(); // Ensure socket is closed if partially initialized
        return false;
    }

    m_connection_active = true; // Set active *before* key exchange & receiver
    if (!exchangeKeys_userID(user_id) || !startReceiver()) {
        cleanup();
        return false;
    }
    return true;
}

// Run the client
bool ChatClient::run() {
    if (!m_connection_active) { // Should be set by initialize
        printf("[System] Client not initialized properly.\n");
        return false;
    }
    messageLoop();
    cleanup(); // Cleanup happens after messageLoop finishes
    printf("[System] Connection closed.\n");
    return true;
}

// --- Main Client Logic ---
int main() {
    // Ignore SIGPIPE, so send() failures are handled by return codes
    // rather than terminating the program.
    signal(SIGPIPE, SIG_IGN);

    char server_ip_str[16] = DEFAULT_IP;
    int server_port_num = DEFAULT_PORT;
    char clientUserId[32];

    printf("Enter server IP (blank for %s): ", DEFAULT_IP);
    if (fgets(server_ip_str, sizeof(server_ip_str), stdin) != NULL) {
        server_ip_str[strcspn(server_ip_str, "\n")] = 0;
        if (server_ip_str[0] == '\0') strcpy(server_ip_str, DEFAULT_IP);
    } else {
        fprintf(stderr, "Error reading server IP. Exiting.\n"); return 1;
    }
    printf("Using IP: %s\n", server_ip_str);

    printf("Enter server port (blank for %d): ", DEFAULT_PORT);
    char port_str[10];
    if (fgets(port_str, sizeof(port_str), stdin) != NULL) {
        port_str[strcspn(port_str, "\n")] = 0;
        if (port_str[0] != '\0') {
            if (sscanf(port_str, "%d", &server_port_num) != 1 || server_port_num <= 0 || server_port_num > 65535) {
                 fprintf(stderr, "Invalid port number. Using default %d.\n", DEFAULT_PORT);
                 server_port_num = DEFAULT_PORT;
            }
        }
    } else {
        fprintf(stderr, "Error reading server port. Exiting.\n"); return 1;
    }
    printf("Using port: %d\n", server_port_num);

    printf("Enter userID: ");
    if (fgets(clientUserId, sizeof(clientUserId), stdin) == NULL) {
        fprintf(stderr, "User ID error\n");
        return 1;
    }
    clientUserId[strcspn(clientUserId, "\n")] = 0;
    if (strlen(clientUserId) == 0) {
        fprintf(stderr, "User ID cannot be empty.\n");
        return 1;
    }


    ChatClient client;
    if (!client.initialize(server_ip_str, server_port_num, clientUserId)) {
        fprintf(stderr, "Client initialization failed.\n");
        return 1;
    }
    
    return client.run() ? 0 : 1;
}