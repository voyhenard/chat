import socket
import threading
import asyncio
import websockets
import json
import signal
import sys
from flask import Flask, render_template, url_for

app = Flask(__name__)
clients = {} #dicionário para controle dos usuários conectados
server_ip = ''

#verifica se o nome de usuário já exixte na lista de usuários
def check_username(username):
    for client in clients:
        if client == username:
            return True #caso já exista retorna verdadeiro
    return False #caso não exista retorna falso

#processa conexão com clientes, é chamada a cada nova conexão, funciona como uma thread
async def handle_client(websocket, path):
    check = True
    while check:
        username = await websocket.recv() #recebe nome de usuário para verificação
        check = check_username(username) #chama função de verificação
        if check:
            message = {'type':'username_check','content':'username already in use'}
            await websocket.send(json.dumps(message)) #se verificação retorna verdadeiro,envia mensagem que usuário já existe ao cliente e aguarda novo nome de usuário

    message = {'type':'username_check','content':'ok'}
    await websocket.send(json.dumps(message)) #se verificação retorna falso, envia ok ao cliente
    clients[username] = websocket #adiciona cliente ao dicionário
    message = {'type':'server_notification','content':'Usuário '+username+' entrou no chat!'}
    print(f'Novo cliente conectado: {username}')
    for client in clients: #envia notificação a todos clientes que um novo usuário está conectado
        await clients[client].send(json.dumps(message))

    while True:
        try:
            message = await websocket.recv() #aguarda novas mensagens do cliente até perder a conexão
            data = {'type':'chat_message','username':username,'content':message}
            for client in clients: #distribui a mensagem para todos os clientes conectados
                await clients[client].send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            break

    clients.pop(username) #retira cliente do dicionário 
    print(f'Cliente desconectado: {username}')
    message = {'type':'server_notification','content':'Usuário '+username+' saiu do chat!'}
    for client in clients: #envia notoficação a todos clientes que um usuário foi desconectado
        await clients[client].send(json.dumps(message))
    await websocket.close()

#servidor http para receber conexões dos clientes web
@app.route("/")
def client():
    return render_template("client.html",server_ip=server_ip)

#inicia servidor http para receber conexões em todos endereços ip da máquina na porta padrão do flask 5000
def start_http_server():
    app.run(host='0.0.0.0')

#inicia servidor websocket para receber conexões em todos endereços ip da máquina na porta 8888
async def start_server():
    host = '0.0.0.0'
    port = 8888

    #servidor websocket
    async def server():
        async with websockets.serve(handle_client, host, port): #aguarda conexões e chama função handle_client para cada cliente
            print(f'Servidor escutando em {host}:{port}')
            await asyncio.Future()  #mantém o servidor em execução indefinidamente

    await server()

#lida com entrada de Ctrl+C no terminal
def handle_keyboard_interrupt(signal, frame):
    print('Encerrando a aplicação...')
    sys.exit(0)

#retorna ip da máquina onde o servidor é excutado, utiliza funções da biblioteca socket
def get_server_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

if __name__ == "__main__":
    server_ip = get_server_ip() #define ip do servidor
    print(f'Server IP: {server_ip}')
    signal.signal(signal.SIGINT, handle_keyboard_interrupt) #recebe Ctrl+C
    thread_flask = threading.Thread(target=start_http_server) #instancia thread para executar servidor http
    thread_flask.start() #inicia thread para execução do servidor http
    asyncio.run(start_server()) #inicia execução do servidor websocket