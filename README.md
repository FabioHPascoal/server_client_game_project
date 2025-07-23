# Snake Battle Multiplayer

Snake Battle é um jogo multiplayer em rede, onde dois jogadores controlam cobras em uma arena para disputar quem sobrevive mais tempo e coleta mais maçãs.

## Descrição

Este projeto foi desenvolvido como critério avaliativo para a disciplina de Redes de Computadores. Ele utiliza comunicação via sockets TCP para gerenciar as interações entre dois jogadores, com interface gráfica feita em Pygame e sprites personalizados.

## Tecnologias Utilizadas

- Python 3
- Pygame
- Sockets TCP (módulo socket)
- Threads para controle simultâneo de conexões

## Como Executar

### Requisitos

- Python 3 instalado
- Pygame: `pip install pygame`

### Execução

1. Clone o repositório:
   ```bash
   git clone github.com/FabioHPascoal/server_client_game_project.git
   cd snake-battle
   ```

2. Inicie o servidor:
   ```bash
   python servidor.py
   ```

3. Em outro terminal ou máquina, inicie o cliente:
   ```bash
   python cliente.py
   ```

## Controles

   Setas do teclado para movimentação nas 4 direções

## Funcionalidades

- Jogo em tempo real entre dois jogadores
- Sprites com rotação automática
- Detecção de colisão e reinício da partida
- Pontuação individual por jogador

## Melhorias Futuras

- Adição de som e efeitos visuais
- Partidas com mais de dois jogadores
- Interface com menu e placar
