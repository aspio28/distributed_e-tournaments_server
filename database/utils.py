import socket
import time
import pickle
import multiprocessing

DNS_ADDRESS = ('172.18.0.250', 5353)

def send_to(payload: bytes, connection: socket.socket):
    buf_size = 2*1024
    sleep_time = 3
    all_good = False
    # Sending attempts after a disconnection error
    attempts = 3
    i = 0
    while i < attempts:
        try:
            total_sent = 0
            start = 0
            while start < len(payload):

                # Calculate remaining length based on payload size and current chunk size
                end = min(len(payload), start + buf_size)

                # Send chunk and keep track of how much was actually sent
                sent = connection.send(payload[start: end])
                total_sent += sent
                start += sent
                print(f"\nSent {total_sent}/{len(payload)} bytes {connection}")
            print(f"\nFinished. Sent {total_sent}/{len(payload)} bytes {connection}")
            all_good = True
            break
        except socket.error as error:
            i += 1
            print(f"{error} while sending data. Attempt {i} after {sleep_time} ms.")
            time.sleep(sleep_time)
            
    if all_good:
        return True
    return False

def _recv(queue, connection):
    return_dict = queue.get()
    buf_size = 2*1024
    data = bytes()
    msg = None
    while True:
        msg = connection.recv(buf_size)
        if msg != None:
            data = data + msg
            try:
                decode = pickle.loads(data)
                print(f"Received data {decode}")
                break
            except:
                pass
    return_dict['data'] = data
    queue.put(return_dict)

def receive_from(connection: socket.socket, wait_time: int):
    
    queue = multiprocessing.Queue()
    queue.put(dict())
    # Create a process to receive data
    process = multiprocessing.Process(target=_recv, args=(queue, connection))  
    process.start()
    process.join(wait_time)

    if process.is_alive():
        print("Timeout occurred!")
        process.terminate()
        process.join()
    if not queue.empty():
        return_dict = queue.get()
        data = return_dict.get('data')
        
    print(f"Received {len(data)} bytes, from {connection}")
    return data
    
def send_and_wait_for_answer(payload: bytes, connection: socket.socket, wait_time:int):
    all_sent = send_to(payload, connection)
    if all_sent:
        response = receive_from(connection, wait_time)
        return all_sent, response
    return False, None


def get_from_dns(domain:str):
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    sock.connect(DNS_ADDRESS)
    request = pickle.dumps(["GET", (domain,)])
    send_to(request, sock)
    data = receive_from(sock, 5)
    result = pickle.loads(data)
    if not result or len(result) == 0:
        raise ConnectionError("Error while connecting to DNS")
    sock.close()
    if result[0] == 'sent_addr':
        return result[1]

def send_addr_to_dns(domain:str, address:tuple, ttl:int=60):
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    sock.connect(DNS_ADDRESS)
    request = pickle.dumps(['POST', (domain, address, ttl)]) 
    return send_to(request, sock)
    
def send_ping_to(address:tuple, data=None):
    """Send a ping message to (ip, port)"""
    try: 
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.connect(address)
        request = pickle.dumps(['ping', (data,)])
        
        send_to(request, sock)
        data = receive_from(sock, 3)
        decoded = pickle.loads(data)
        
        if 'ECHO' in decoded:
            sock.close()
            return True
    except Exception as err :
        print('ping error: ',err)
    sock.close()
    return False

def send_echo_replay(arguments, connection:socket.socket, address):
    """answer a ping message"""
    answer = pickle.dumps(['ECHO', (None,)])
    all_good = send_to(answer, connection)
    return all_good