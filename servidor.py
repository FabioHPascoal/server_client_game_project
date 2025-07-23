""# servidor.py - Servidor do jogo Snake Battle

import socket
import threading
import json
import time
import logging
import random

# === Configurações ===
GRID_W, GRID_H = 32, 24
TAM_CELULA = 20
PORTA = 12345
HOST = "localhost"

# === Direções possíveis ===
DIRECOES = {
    "cima": (0, -1),
    "baixo": (0, 1),
    "esquerda": (-1, 0),
    "direita": (1, 0)
}

# === Estado do jogo ===
jogadores = {
    1: {"corpo": [[5, 5], [4, 5]], "direcao": "direita", "vivo": True, "pontos": 0},
    2: {"corpo": [[26, 18], [27, 18]], "direcao": "esquerda", "vivo": True, "pontos": 0}
}

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
            if comando.get("acao") == "direcao":
                with lock:
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
    if x < 0 or y < 0 or x >= GRID_W or y >= GRID_H:
        return True
    if cobra["corpo"][0] in cobra["corpo"][1:]:
        return True
    for outra in outras:
        if cobra["corpo"][0] in outra["corpo"]:
            return True
    return False

def reiniciar_jogo():
    global jogadores, maca, jogo_em_andamento

    jogadores[1] = {"corpo": [[5, 5], [4, 5]], "direcao": "direita", "vivo": True, "pontos": 0}
    jogadores[2] = {"corpo": [[26, 18], [27, 18]], "direcao": "esquerda", "vivo": True, "pontos": 0}

    maca = [random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1)]
    jogo_em_andamento = True

def enviar_estado(clientes):
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

def main():
    global maca, jogo_em_andamento

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(threadName)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((HOST, PORTA))
    servidor.listen(2)
    logging.info("Servidor aguardando conexões...")

    clientes = []
    for i in range(2):
        conn, addr = servidor.accept()
        logging.info(f"Conexão aceita de {addr}")
        t = threading.Thread(target=tratar_cliente, args=(conn, i + 1), daemon=True)
        t.start()
        clientes.append(conn)

    time_morte = 0
    while True:
        with lock:
            if jogo_em_andamento:
                vivos = [j for j in jogadores.values() if j["vivo"]]
                if len(vivos) <= 1:
                    jogo_em_andamento = False
                    time_morte = time.time()

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
                        jogador["pontos"] += 1
                        cobra_que_comeu = pid
                        maca = [random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1)]
                        break

                for pid, jogador in jogadores.items():
                    if jogador["vivo"] and pid != cobra_que_comeu:
                        jogador["corpo"].pop()

            else:
                if time.time() - time_morte > 3:
                    reiniciar_jogo()

        enviar_estado(clientes)
        time.sleep(0.5)

if __name__ == "__main__":
    main()