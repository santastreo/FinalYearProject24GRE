# Chat Application with Abuse Detection

This is a chat application built in Python, featuring abuse detection using BERT (Bidirectional Encoder Representations from Transformers). It consists of two parts: a server (`chat_server.py`) and a client (`chat_client.py`).

## Requirements

To run this application, you will need Python 3.7 or later. Additionally, you need to install several packages. You can install them using pip:

```
pip install torch transformers tkinter
```

Note: `tkinter` usually comes pre-installed with Python. If it's not installed on your machine, you can find installation instructions at https://tkdocs.com/tutorial/install.html.

## Running the Server

1. Navigate to the directory containing `chat_server.py`.
2. Run the server script in your IDE or from the command line using:
   ```
   python chat_server.py
   ```
3. You should get a message in the terminal saying `Server is listening...`. Keep the server running to accept client connections.

## Running the Client

1. Open a new terminal or command prompt window.
2. Navigate to the directory containing `chat_client.py`.
3. Run the client script in your IDE or from the command line using:
   ```
   python chat_client.py
   ```
4. Repeat the step to connect another client to the server.

Note: if you are using VS Code, you might want to run the first client in an interactive window, and run the other client in a dedicated window.

## Usage

- After starting the client application, enter your desired username.
- You can then send messages to the chat, which will be visible to all connected clients.
- The server uses BERT to detect any abusive language in the context of the recent messages. If such language is detected, the server will issue warnings or disconnect the user after 3 repeated offenses.
- All messages, along with their timestamps, are logged in `server_chat_log.txt` and `client_chat_log.txt` files in their respective directories.

## Notes

- The server and clients are configured to run on `localhost` (127.0.0.1) with port 65432.
- Ensure that the required port is open and not blocked by any firewall.
- The BERT model used is 'bert-base-uncased', and it is set to run on the CPU.
- The server requires the `model_state_dict.pth` file in the `Model` folder within the same directory as `chat_server.py`. Make sure this file is present before running the server.