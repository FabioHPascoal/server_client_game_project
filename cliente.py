import socket
import threading
import json
import pygame as pg
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(threadName)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Constantes de conexão e jogo
HOST = "localhost"
PORTA = 12345
TAM_CELULA = 20
RES_ORIGINAL = (640, 480)
RES_ESCALADA = (1280, 960)

# Variáveis globais
jogador_id = None
estado_jogo = {}

def receber_dados(sock):
    global estado_jogo
    buffer = ""
    while True:
        try:
            data = sock.recv(4096).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                linha, buffer = buffer.split("\n", 1)
                if not linha.strip():
                    continue
                estado = json.loads(linha)
                if estado.get("tipo") == "estado":
                    estado_jogo = estado
        except Exception as e:
            logging.error(f"Erro ao receber dados: {e}")
            break

def carregar_sprites():
    def carregar(caminho):
        return pg.image.load(caminho).convert_alpha()

    return {
        1: {k: carregar(f"assets/cobra1_{k}.png") for k in ["head", "tail", "body_straight", "body_curve"]},
        2: {k: carregar(f"assets/cobra2_{k}.png") for k in ["head", "tail", "body_straight", "body_curve"]},
        "maca": carregar("assets/maca.png"),
        "fundo": pg.image.load("assets/fundo.png").convert()
    }

def direcao_entre(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return {
        (1, 0): "direita", (-1, 0): "esquerda",
        (0, 1): "baixo", (0, -1): "cima"
    }.get((dx, dy))

def rotacionar(sprite, direcao):
    angulos = {"cima": 0, "direita": -90, "baixo": 180, "esquerda": 90}
    return pg.transform.rotate(sprite, angulos[direcao])

def tratar_eventos_input(direcao_atual):
    keys = pg.key.get_pressed()
    nova = direcao_atual

    if jogador_id == 1:
        if keys[pg.K_UP]: nova = "cima"
        if keys[pg.K_DOWN]: nova = "baixo"
        if keys[pg.K_LEFT]: nova = "esquerda"
        if keys[pg.K_RIGHT]: nova = "direita"
    elif jogador_id == 2:
        if keys[pg.K_w]: nova = "cima"
        if keys[pg.K_s]: nova = "baixo"
        if keys[pg.K_a]: nova = "esquerda"
        if keys[pg.K_d]: nova = "direita"

    return nova if nova != direcao_atual else None

def desenhar_cobra(tela, corpo, sprites):
    for i, pos in enumerate(corpo):
        x, y = pos[0] * TAM_CELULA, pos[1] * TAM_CELULA

        if i == 0:
            prox = corpo[1]
            direcao = direcao_entre(pos, prox)
            img = rotacionar(sprites["head"], direcao)

        elif i == len(corpo) - 1:
            ant = corpo[i - 1]
            direcao = direcao_entre(ant, pos)
            img = rotacionar(sprites["tail"], direcao)

        else:
            ant, prox = corpo[i - 1], corpo[i + 1]
            da, dp = direcao_entre(pos, ant), direcao_entre(pos, prox)

            if da == dp or {da, dp} in [{"cima", "baixo"}, {"esquerda", "direita"}]:
                img = rotacionar(sprites["body_straight"], da)
            else:
                curvas = {
                    ("cima", "direita"): 0, ("direita", "cima"): 0,
                    ("direita", "baixo"): -90, ("baixo", "direita"): -90,
                    ("baixo", "esquerda"): 180, ("esquerda", "baixo"): 180,
                    ("esquerda", "cima"): 90, ("cima", "esquerda"): 90
                }

                if da is not None and dp is not None: angulo = curvas.get((da, dp), 0)
                else:angulo = 0
                
                img = pg.transform.rotate(sprites["body_curve"], angulo)

        tela.blit(img, (x, y))

def main():
    global jogador_id, estado_jogo

    try:
        # Conexão com o servidor
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORTA))

        buffer = ""
        while not jogador_id:
            buffer += sock.recv(1024).decode()
            if "\n" in buffer:
                linha, buffer = buffer.split("\n", 1)
                jogador_id = json.loads(linha)["id"]

        threading.Thread(target=receber_dados, args=(sock,), daemon=True).start()

        # Inicialização do Pygame
        pg.init()
        tela = pg.display.set_mode(RES_ESCALADA)
        tela_base = pg.Surface(RES_ORIGINAL)
        pg.display.set_caption(f"Snake Battle - Jogador {jogador_id}")
        relogio = pg.time.Clock()

        fonte = pg.font.SysFont("Arial", 24)
        grande = pg.font.SysFont("Arial", 36)
        sprites = carregar_sprites()
        direcao_atual = "direita" if jogador_id == 1 else "esquerda"

        while True:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    return

            nova = tratar_eventos_input(direcao_atual)
            if nova:
                try:
                    sock.sendall(json.dumps({"acao": "direcao", "direcao": nova}).encode())
                    direcao_atual = nova
                except Exception as e:
                    logging.error(f"Erro ao enviar comando: {e}")
                    break

            tela_base.blit(sprites["fundo"], (0, 0))

            if estado_jogo.get("jogadores"):
                # Maçã
                mx, my = estado_jogo.get("maca", [15, 12])
                tela_base.blit(sprites["maca"], (mx * TAM_CELULA, my * TAM_CELULA))

                # Cobras
                for pid, jogador in estado_jogo["jogadores"].items():
                    if jogador["vivo"]:
                        desenhar_cobra(tela_base, jogador["corpo"], sprites[int(pid)])

                # Pontuação
                tela_base.blit(fonte.render(f"Jogador 1: {estado_jogo['jogadores']['1']['pontos']}", True, (0, 0, 0)), (10, 5))
                tela_base.blit(fonte.render(f"Jogador 2: {estado_jogo['jogadores']['2']['pontos']}", True, (0, 0, 0)), (450, 5))

                # Mensagens de status
                vivo = estado_jogo["jogadores"][str(jogador_id)]["vivo"]
                em_jogo = estado_jogo.get("em_andamento", True)
                if not vivo:
                    tela_base.blit(grande.render("Você morreu!", True, (0, 0, 0)), (220, 200))
                elif not em_jogo and vivo:
                    tela_base.blit(grande.render("Você venceu!", True, (0, 0, 0)), (220, 200))
                if not em_jogo:
                    tela_base.blit(fonte.render("Reiniciando...", True, (0, 0, 0)), (250, 240))

            tela.blit(pg.transform.scale(tela_base, RES_ESCALADA), (0, 0))
            pg.display.flip()
            relogio.tick(60)

    except Exception as e:
        logging.error(f"Erro no cliente: {e}")

if __name__ == "__main__":
    main()
