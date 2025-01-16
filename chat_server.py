# server script acts as the controller, which houses the trained detection model and message buffer, and has rules that creates a
# moderated, safe chat environment 

# Importing necessary libraries
import os
import socket
import threading
import torch #for loading the trained model
from transformers import BertTokenizer, BertForSequenceClassification
from collections import defaultdict, deque
from datetime import datetime, timedelta

# setting the model to  use the CPU
device = torch.device('cpu')

## models structure is required for loading a state dict

# initialising the bert model and its tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2) 

## state dict has the trained weights and biases but not the models structure

# loading the trained model as a state dictionary
model_path = os.path.join(os.path.dirname(__file__), 'Model', 'model_state_dict.pth')


#loading models state dictionary, moves the model to cpu and sets it to evaluation mode.
model.load_state_dict(torch.load(model_path, map_location=device))
model.to(device)
model.eval()


# here we define the default IP and PORT for the server
# server creates a socket and listens for incoming messages from the clients.
HOST = '127.0.0.1'
PORT = 65432

# Maintains lists to track connected clients and their respective names
clients = []
names = []


# initalises two attributes, self.messages and self.retention_period
class MessageBuffer:
    # constructor that creates a new messagebuffer object
    def __init__(self, retention_period=timedelta(minutes=5)): 
        # initalises two attributes, self.messages and self.retention_period
        self.messages = deque()
        self.retention_period = retention_period 
        
    # add new message to the deque
    def add_message(self, message):
        timestamp = datetime.now() 
        self.messages.append((timestamp, message)) #appends msg as a tuple to the deque
        self.clean_old_messages() # call this function to remove any messages that have exceeeded the retention period

    def get_context(self):
        #retreives a string containing all messages currently in buffer, separated by spaces
        #and extracts only message text (not timestamps) from the tuples in the deque
        return " ".join(message for _, message in self.messages)
    
    #removes messages that are older than 5 minutes
    def clean_old_messages(self):
        current_time = datetime.now()
        #Iteratively removes messages from the front if they are older than the retention period
        while self.messages and current_time - self.messages[0][0] > self.retention_period:
            self.messages.popleft()



#creates a defaultdict where each key is a client name and the value is a messagebuffer object
recent_messages = defaultdict(MessageBuffer) 

## [defaultdict provides default value for the key that does not exists, and never raises a key error] ##

## [defaultdict also organises and manages message buffers for different clients efficiently] ##

#an empty dictionary that keeps track of the number of warnings for each client
warnings = {} 


# setting up the server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

def classify_with_bert(text):
    # Ensure the model is in evaluation mode and on the CPU
    model.eval()
    model.to('cpu')

    # Prepare the text for BERT using the tokenizer
    inputs = tokenizer.encode_plus(
        text,
        add_special_tokens=True,
        max_length=512,
        return_tensors='pt',
        padding='max_length',
        truncation=True
    )

    # Get predictions from the model
    with torch.no_grad():
        outputs = model(**inputs)

    # Convert logits to probabilities
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

    # the second label in dataset (index 1) is for abusive comments
    # we compare the probability to the threshold 0.5 to get a True/False value
    is_abusive = probs[:, 1] > 0.5 #(can be tested with different values to see perforamce increase/decrease)

    # Convert the tensor to a Python boolean if it's a single-element tensor
    return is_abusive.item()

# sends the list of connected users to all the clients
def send_users_list():
    users = ' '.join(names)
    for client in clients:
        client.send(f'USERS {users}'.encode('utf-8'))

# this function stores messages in a text file
def log_message(message):
    log_path = os.path.join(os.path.dirname(__file__), 'server_chat_log.txt')
    with open(log_path, "a") as file:
        file.write(message + "\n")


#function that handles broadcasting a message from one client to the other
#sends a message to all clients, with options to exclude the sender and modify the message for the sender
def broadcast(message, sender_client, exclude_sender):
    for client in clients:
        try:
            if isinstance(message, str):
                message = message.encode('utf-8')
            
            if client == sender_client:
                if not exclude_sender:
                    if ':' in message.decode('utf-8'):
                        message_content = message.decode('utf-8').split(': ', 1)[1]
                        modified_message = f"[you]: {message_content}"
                    else:
                        modified_message = f"[you]: {message.decode('utf-8')}"
                    client.send(modified_message.encode('utf-8'))
                else:
                    continue
            else:
                client.send(message)
                log_message(message.decode('utf-8'))
        except Exception as e:
            print(f"An error occurred while sending to client: {e}")
            remove_client(client)

#function to handle a client leaving the chat, and also displaying a message on screen
def remove_client(client):
    if client not in clients:
        return
    index = clients.index(client)
    name = names[index]

    warnings.pop(name, None)

    print(f"Removing client: {name}")

    clients.remove(client)
    names.remove(name)
    client.close()

    leave_message = f"INFO: {name} has left the chat."
    print(f"Broadcasting: {leave_message}") 
    broadcast(leave_message, None, False)


#in this function, messages are added to the buffer as they are received, and the context is retrieved by concatenating the recent messages within the retention period.
# this function continuously receives messages from a client, processes them, checks for toxicity, and handles warnings and disconnections accordingly.
def handle(client):
    name = names[clients.index(client)]
    while True:
        try:
            raw_message = client.recv(1024)
            if not raw_message:
                print(f"Empty message, removing client.")
                remove_client(client)
                break
            message = raw_message.decode('utf-8')
            print(f"Received message: {message}")
            name = names[clients.index(client)]
            
            recent_messages[name].add_message(message)
            context = recent_messages[name].get_context()

            print(f"Classifying message for abuse detection with context")
            is_toxic = classify_with_bert(context)
            if is_toxic:
                warnings[name] = warnings.get(name, 0) + 1
                if warnings[name] == 1:
                    warning_message = "WARNING: Stop using profanity and behave decently"
                elif warnings[name] == 2:
                    warning_message = "WARNING: This is your final warning, you will be kicked out if you bully again"
                elif warnings[name] >= 3:
                    client.send("DISCONNECT You have been removed from the chat due to repeated bullying.".encode('utf-8'))
                    remove_client(client)
                    broadcast(f"{name} has been removed from the chat due to repeated bullying.", None, False)
                    break 
                client.send(warning_message.encode('utf-8'))
                if warnings[name] < 3:
                    hidden_msg_notification = "Offensive language was detected and hidden."
                    broadcast(hidden_msg_notification, client, True)
            else:
                broadcast(f"{name}: {message}".encode('utf-8'), client, exclude_sender=False)
        except ConnectionError:
            print(f"Client {name} disconnected.")
            remove_client(client)
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

# continuously accepts new client connections, starts a new thread for handling each client
def receive():
    while True:
        client, addr = server.accept()
        print(f"Connected with {str(addr)}")
        
        client.send('NAME'.encode('utf-8'))
        name = client.recv(1024).decode('utf-8')
        names.append(name)
        clients.append(client)
        
        print(f"Name of the client is {name}")
        
        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

        broadcast(f"INFO:{name} joined the chat!".encode('utf-8'), None, False)
        send_users_list()

print("Server is listening...")
receive()
