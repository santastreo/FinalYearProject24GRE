# client script acts as the connector, allowing users to interact with each other through a Graphical User Interface

# Importing necessary libraries
import os
import socket #for network connection with server and client
import threading #for handling multiple clients 
import tkinter as tk #for creating GUI
from tkinter import simpledialog, messagebox, scrolledtext, font as tkFont
import datetime


# Define server details to connect to
HOST = '127.0.0.1'
PORT = 65432

# Create a socket object and establish a connection to the server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

# Create a ChatApp class which extends tk.Tk
class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("Online Chat for Abuse Detection")
        self.geometry("550x650")
        self.configure(bg="#303030")

        # Custom font
        self.customFont = tkFont.Font(family="Arial", size=12)

        # Chat frame - Main frame for the chat display
        self.chat_frame = tk.Frame(self, bg="#424242")
        self.chat_frame.pack(pady=15, padx=15, fill=tk.BOTH, expand=True)

        # Chat box - Text area to show messages
        self.chat_box = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, state=tk.DISABLED, bg="#E0E0E0", font=self.customFont)
        self.chat_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure tags for different message types / elements within the conversation
        self.chat_box.tag_configure('red', foreground='red')
        self.chat_box.tag_configure('green', foreground='green')
        self.chat_box.tag_configure('black', foreground='black')

        # Active users list - Displays active users
        self.users_listbox = tk.Listbox(self.chat_frame, bg="#D0D0D0", font=self.customFont)
        self.users_listbox.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Message entry - Where the user types messages 
        self.text_entry = tk.Entry(self, width=30, font=self.customFont)
        self.text_entry.pack(pady=15, padx=15, side=tk.LEFT, fill=tk.X, expand=True)
        self.text_entry.bind("<Return>", self.send_msg_via_enter)

        # Send button
        self.send_button = tk.Button(self, text="Send", command=self.send_msg, bg="#4CAF50", activebackground="#45a049", font=self.customFont)
        self.send_button.pack(pady=15, padx=15, side=tk.RIGHT)

        # Close event binding
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start receive thread
        self.start_receive_thread()
        
    # logging chat to a text file
    def log_message(self, message):
        log_path = os.path.join(os.path.dirname(__file__), 'client_chat_log.txt') 
        with open(log_path, "a") as file:
            file.write(message + "\n")    

    # displays the messages onto the chatbox, alongside their timestamp
    def display_message(self, message, color='black'):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.insert(tk.END, formatted_message + "\n", color)
        self.chat_box.config(state=tk.DISABLED)
        self.chat_box.see(tk.END)

        # Log the message
        self.log_message(formatted_message)

    # Function to send a message to the server
    def send_msg(self):
        msg = self.text_entry.get()
        if msg:
            client.send(msg.encode('utf-8'))
            self.text_entry.delete(0, tk.END)

    # Allows to send message by just pressing enter button
    def send_msg_via_enter(self, event=None):
        self.send_msg()

    # Function to update the list of active users
    def update_users_list(self, users):
        self.users_listbox.delete(0, tk.END)
        for user in users:
            self.users_listbox.insert(tk.END, user)

    # this function continuously listens for and handles incoming messages from the server, and updates each client with the info
    # runs on a separate thread
    def receive_msg(self):
     while True:
        try:
            message = client.recv(1024).decode('utf-8') # receives message from server

            # Handle disconnection message
            if message.startswith('DISCONNECT'):
                info_message = message.split(' ', 1)[1]  # Split off the DISCONNECT keyword
                self.display_message(info_message, 'red')
                client.close()  # Close the client socket
                self.send_button.config(state=tk.DISABLED)  # Disable the send button
                break  # Exit the while loop

            elif message == 'NAME': # if server requests client name, send the username 
                client.send(self.username.encode('utf-8'))
            elif message.startswith('USERS'): # If the server sends an updated list of users
                users = message.split()[1:]
                self.update_users_list(users)
            elif message.startswith("INFO:"): # If the server sends an informational message
                info_message = message.split("INFO:")[1]
                self.display_message(info_message, 'green')
            elif message.startswith("WARNING:"): # If the server sends a warning message
                warning_message = message.split("WARNING:")[1]
                self.display_message(warning_message, 'red')
            elif message.startswith("BULLYING"): # If the server indicates a bullying message was detected
                self.display_message("Bullying message detected it has been hidden", 'red')
            else:
                self.display_message(message)

        except ConnectionResetError:
            messagebox.showerror("Connection Error", "Connection to the server was lost.")
            break
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            if isinstance(e, OSError):
                break

    # Function to start a new thread for receiving messages - prompts the user for consent, then a username
    def start_receive_thread(self):
        # alert window
        consent = messagebox.askokcancel("Moderated Chat Environment",
                                        "This is a moderated chat environment. If you are abusive towards others, you will be kicked out. If you consent, please press 'OK' and continue, otherwise if you wish to opt out, please press 'Cancel' and exit now.")
        if not consent:
            self.destroy() 
            return
        # user setting a name
        while True:
            self.username = simpledialog.askstring("Username", "Choose a username", parent=self)
            if not self.username:
                # error handling
                retry = messagebox.askretrycancel("Error", "You must enter a username. Retry?")
                if not retry:
                    self.destroy()
                    return
            else:
                break

        thread = threading.Thread(target=self.receive_msg)
        thread.daemon = True
        thread.start()

    # Function to handle the event when the window is closed
    def on_closing(self):
        messagebox.showinfo("Info", "Closing chat application...")
        client.close()
        self.destroy()

# Execute the GUI
if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()
