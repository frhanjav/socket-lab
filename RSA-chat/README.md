Compile the server:

```
g++ server_linux.cpp -o server_linux -lpthread -lstdc++
```

Compile the client:

```
g++ client_linux.cpp -o client_linux -lpthread -lstdc++
```

Run the server:

```
./server_linux
```

It will ask for a port number.

In another terminal, run one or more clients:

```
./client_linux
```

communicate using (user_id)/(message)