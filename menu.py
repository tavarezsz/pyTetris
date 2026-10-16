"""Tela de criação e entrada em sessões multiplayer."""

from queue import Empty
import socket

import pygame

from sockets.client_tcp import ConexaoCliente
from sockets.server_tcp import ServidorSessao


TAMANHO_MENU = (460, 600)


def desenhar_menu(tela, estado, host, porta, foco, status="", erro=""):
    tela.fill((18, 18, 25))
    titulo = pygame.font.Font(None, 48)
    fonte = pygame.font.Font(None, 26)
    pequena = pygame.font.Font(None, 22)
    botoes, campos = {}, {}

    def texto(conteudo, x, y, cor=(235, 235, 245), tipo=fonte):
        tela.blit(tipo.render(conteudo, True, cor), (x, y))

    def paragrafo(conteudo, y, cor):
        linha = ""
        for palavra in conteudo.split():
            tentativa = f"{linha} {palavra}".strip()
            if pequena.size(tentativa)[0] > 396:
                texto(linha, 32, y, cor, pequena)
                y += 24
                linha = palavra
            else:
                linha = tentativa
        texto(linha, 32, y, cor, pequena)

    def botao(chave, rotulo, y, destaque=False):
        ret = pygame.Rect(32, y, 396, 52)
        cor = (55, 100, 90) if destaque else (35, 40, 55)
        if ret.collidepoint(pygame.mouse.get_pos()):
            cor = tuple(min(255, c + 18) for c in cor)
        pygame.draw.rect(tela, cor, ret, border_radius=10)
        imagem = fonte.render(rotulo, True, (245, 245, 250))
        tela.blit(imagem, imagem.get_rect(center=ret.center))
        botoes[chave] = ret

    def campo(chave, rotulo, valor, y, placeholder=""):
        texto(rotulo, 32, y - 26, (170, 180, 200), pequena)
        ret = pygame.Rect(32, y, 396, 46)
        pygame.draw.rect(tela, (25, 28, 40), ret, border_radius=8)
        cor = (100, 230, 160) if foco == chave else (70, 80, 100)
        pygame.draw.rect(tela, cor, ret, width=2, border_radius=8)
        # Mostra o final do texto longo, incluindo onde o usuário está digitando.
        visivel = valor or placeholder
        while fonte.size(visivel)[0] > 364:
            visivel = visivel[1:]
        texto(visivel, 44, y + 13, (235, 235, 245) if valor else (110, 120, 140))
        campos[chave] = ret

    texto("TETRIS DUEL", 32, 42, (100, 230, 160), titulo)
    if estado == "inicio":
        paragrafo("Crie uma sessão neste computador ou entre na sessão de um amigo.\n Somente em LAN ou VPN ", 170,
                  (200, 205, 220))
        botao("criar", "Criar sessão", 260, True)
        botao("entrar", "Entrar em sessão", 326)
    elif estado in ("criar", "entrar"):
        texto("Criar sessão" if estado == "criar" else "Entrar em sessão", 32, 150)
        if estado == "entrar":
            campo("host", "IP ou nome do servidor", host, 218, "Ex.: 192.168.1.20")
            campo("porta", "Porta TCP", porta, 298)
        else:
            campo("porta", "Porta TCP", porta, 218)
            paragrafo("O servidor e o seu jogo rodam neste computador. Compartilhe seu IP e esta porta com o convidado.",
                      286, (170, 180, 200))
        if erro:
            paragrafo(erro, 368, (255, 140, 140))
        botao("conectar", "Criar e aguardar" if estado == "criar" else "Conectar", 444, True)
        botao("voltar", "Voltar", 510)
    else:
        texto("Aguardando a partida", 32, 170)
        paragrafo(status, 230, (200, 205, 220))
        paragrafo("O jogo começa automaticamente quando os dois jogadores estiverem conectados.",
                  334, (170, 180, 200))
        botao("voltar", "Cancelar", 470)
    return botoes, campos


def main():
    from main import main as iniciar_jogo

    pygame.init()
    tela = pygame.display.set_mode(TAMANHO_MENU)
    pygame.display.set_caption("Tetris | Sessões")
    pygame.key.set_repeat(300, 35)
    relogio = pygame.time.Clock()
    estado, host, porta, foco = "inicio", "", "6000", "host"
    status = erro = ""
    cliente = servidor = None
    executando = True

    def encerrar_sessao():
        nonlocal cliente, servidor
        if cliente is not None:
            cliente.encerrar()
            cliente = None
        if servidor is not None:
            servidor.encerrar()
            servidor = None

    try:
        while executando:
            relogio.tick(60)
            botoes, campos = desenhar_menu(tela, estado, host, porta, foco, status, erro)
            acao = None
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    executando = False
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    for nome, ret in campos.items():
                        if ret.collidepoint(evento.pos):
                            foco = nome
                    for nome, ret in botoes.items():
                        if ret.collidepoint(evento.pos):
                            acao = nome
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        if estado == "inicio":
                            executando = False
                        else:
                            acao = "voltar"
                    elif estado in ("criar", "entrar"):
                        if evento.key == pygame.K_RETURN:
                            acao = "conectar"
                        elif evento.key == pygame.K_TAB:
                            foco = "porta" if foco == "host" or estado == "criar" else "host"
                        elif evento.key == pygame.K_BACKSPACE:
                            if foco == "porta":
                                porta = porta[:-1]
                            else:
                                host = host[:-1]
                        elif evento.unicode and evento.unicode.isprintable():
                            if foco == "porta" and evento.unicode in "0123456789":
                                porta = (porta + evento.unicode)[:5]
                            elif foco == "host" and not evento.unicode.isspace():
                                host = (host + evento.unicode)[:253]

            if not executando:
                break
            if acao in ("criar", "entrar"):
                estado = acao
                foco = "porta" if estado == "criar" else "host"
                erro = ""
            elif acao == "voltar":
                encerrar_sessao()
                estado, erro = "inicio", ""
            elif acao == "conectar":
                try:
                    numero_porta = int(porta)
                    if not 1 <= numero_porta <= 65535:
                        raise ValueError("Informe uma porta entre 1 e 65535.")
                    if estado == "entrar" and not host.strip():
                        raise ValueError("Informe o endereço do servidor.")
                    criando = estado == "criar"
                    if criando:
                        servidor = ServidorSessao(porta=numero_porta)
                        servidor.iniciar()
                    cliente = ConexaoCliente("127.0.0.1" if criando else host.strip(), numero_porta)
                    cliente.iniciar()
                    status = f"Conectando a {cliente.host}:{numero_porta}..."
                    estado = "aguardando"
                except (OSError, ValueError) as falha:
                    encerrar_sessao()
                    erro = f"Não foi possível abrir a sessão: {falha}"

            if estado == "aguardando" and cliente is not None:
                while True:
                    try:
                        mensagem = cliente.fila_entrada.get_nowait()
                    except Empty:
                        break
                    if mensagem["tipo"] == "aguardando":
                        if servidor is not None:
                            try:
                                ip = socket.gethostbyname(socket.gethostname())
                            except OSError:
                                ip = "consulte o IP deste computador"
                            status = f"Sessão criada! IP local detectado: {ip}. Porta: {porta}. Aguardando o convidado..."
                        else:
                            status = "Conectado! Aguardando o outro jogador..."
                    elif mensagem["tipo"] == "inicio":
                        voltar = iniciar_jogo(seed=mensagem["seed"],
                                              fila_entrada=cliente.fila_entrada,
                                              fila_saida=cliente.fila_saida)
                        encerrar_sessao()
                        if not voltar:
                            executando = False
                            break
                        pygame.init()
                        tela = pygame.display.set_mode(TAMANHO_MENU)
                        pygame.display.set_caption("Tetris | Sessões")
                        pygame.key.set_repeat(300, 35)
                        estado, erro = "inicio", ""
                        break
                    elif mensagem["tipo"] in ("erro_rede", "conexao_encerrada"):
                        criando = servidor is not None
                        encerrar_sessao()
                        estado = "criar" if criando else "entrar"
                        erro = mensagem.get("texto", "O servidor encerrou a conexão.")
                        break
            if executando:
                pygame.display.flip()
    finally:
        encerrar_sessao()
        pygame.quit()


if __name__ == "__main__":
    main()
