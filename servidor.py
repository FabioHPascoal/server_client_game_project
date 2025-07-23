import socket
import threading
import json
import time
import logging
import random

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(threadName)s] %(message)s',
    datefmt='%H:%M:%S'
)

GRID_W, GRID_H = 32, 24
TAM_CELULA = 20

DIRECOES = {
    "cima": (0, -1),
    "baixo": (0, 1),
    "esquerda": (-1, 0),
    "direita": (1, 0)
}

jogadores = {
    1: {"corpo": [[5, 5], [4, 5]], "direcao": "direita", "vivo": True, "vitorias": 0},
    2: {"corpo": [[26, 18], [27, 18]], "direcao": "esquerda", "vivo": True, "vitorias": 0}
}

# A fila de comandos é protegida por um lock para evitar condições de corrida
comandos = {1: [], 2: []}
lock = threading.Lock()

maca = [random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1)]
jogo_em_andamento = True

def tratar_cliente(conn, jogador_id):
    logging.info(f"Jogador {jogador_id} conectado.")
    try:
        conn.sendall((json.dumps({"tipo": "conexao", "id": jogador_id}) + "\n").encode())
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            comando = json.loads(data)
            
            # Para teste de latência
            if comando["acao"] == "ping":
                inicio = time.time()
                conn.sendall((json.dumps({"tipo": "pong", "timestamp": inicio}) + "\n").encode())
                continue
            
            with lock:
                if comando["acao"] == "direcao":
                    comandos[jogador_id].append(comando["direcao"])

    except Exception as e:
        logging.error(f"Erro com jogador {jogador_id}: {e}")
    
    finally:
        conn.close()
        logging.info(f"Jogador {jogador_id} desconectado.")

def mover_cobra(cobra):
    dx, dy = DIRECOES[cobra["direcao"]]
    cabeca = cobra["corpo"][0]
    nova_cabeca = [cabeca[0] + dx, cabeca[1] + dy]
    cobra["corpo"].insert(0, nova_cabeca)

def colisao(cobra, outras):
    x, y = cobra["corpo"][0]
    
    # Verificação de colisão com as paredes
    if x < 0 or y < 0 or x >= GRID_W or y >= GRID_H:
        return True
    
    # Verificação de colisão com o próprio corpo
    if cobra["corpo"][0] in cobra["corpo"][1:]:
        return True
    
    # Verificação de colisão com outras cobras
    for outra in outras:
        if cobra["corpo"][0] in outra["corpo"]:
            return True
        
    return False

def reiniciar_jogo():
    global jogadores, maca, jogo_em_andamento
    jogadores[1]["corpo"] = [[5, 5], [4, 5]]
    jogadores[2]["corpo"] = [[26, 18], [27, 18]]
    jogadores[1]["direcao"] = "direita"
    jogadores[2]["direcao"] = "esquerda"
    jogadores[1]["vivo"] = True
    jogadores[2]["vivo"] = True
    maca = [random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1)]
    jogo_em_andamento = True

def main():
    global maca, jogo_em_andamento

    time_morte = time.time() # Inicialização time para contar o tempo após a morte

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("localhost", 12345))
    servidor.listen(2)
    logging.info("Servidor aguardando conexões...")

    clientes = []
    for i in range(2):
        conn, addr = servidor.accept()
        logging.info(f"Conexão aceita de {addr}")
        t = threading.Thread(target=tratar_cliente, args=(conn, i + 1), daemon=True)
        t.start()
        clientes.append(conn)

    while True:
        with lock:
            if jogo_em_andamento:
                vivos = [j for j in jogadores.values() if j["vivo"]]
                if len(vivos) <= 1:
                    jogo_em_andamento = False
                    time_morte = time.time()

                    for pid, j in jogadores.items():
                        if j["vivo"]:
                            jogadores[pid]["vitorias"] += 1

                for pid in jogadores:
                    if comandos[pid]:
                        nova = comandos[pid].pop(0)
                        atual = jogadores[pid]["direcao"]
                        if (atual, nova) not in [("cima", "baixo"), ("baixo", "cima"), ("esquerda", "direita"), ("direita", "esquerda")]:
                            jogadores[pid]["direcao"] = nova

                for pid in jogadores:
                    if jogadores[pid]["vivo"]:
                        mover_cobra(jogadores[pid])

                for pid in jogadores:
                    if not jogadores[pid]["vivo"]:
                        continue
                    outras = [j for p, j in jogadores.items() if p != pid and j["vivo"]]
                    if colisao(jogadores[pid], outras):
                        jogadores[pid]["vivo"] = False

                cobra_que_comeu = None
                for pid, jogador in jogadores.items():
                    if jogador["vivo"] and jogador["corpo"][0] == maca:
                        cobra_que_comeu = pid
                        maca = [random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1)]
                        break

                for pid, jogador in jogadores.items():
                    if jogador["vivo"] and pid != cobra_que_comeu:
                        jogador["corpo"].pop()

            else:
                if time.time() - time_morte > 3:
                    reiniciar_jogo()

        estado = {
            "tipo": "estado",
            "jogadores": jogadores,
            "maca": maca,
            "em_andamento": jogo_em_andamento
        }

        msg = json.dumps(estado) + "\n"
        for c in clientes:
            try:
                c.sendall(msg.encode())
            except Exception as e:
                logging.warning(f"Erro ao enviar estado: {e}")

        # Controla a velocidade do servidor
        time.sleep(0.2)

if __name__ == "__main__":
    main()
