"""Protótipo: setas movem, Z gira e R reinicia; linhas cheias somem com animação."""

import argparse
from queue import Empty, Queue

import pygame

from gerador_pecas import GeradorPecas, gerar_seed
from pecas import Peca
from tabuleiro import Tabuleiro
from sockets.protocolo import validar_estado_tabuleiro


TAMANHO_CELULA = 30
ALTURA_CABECALHO = 64
LARGURA_PAINEL_ADVERSARIO = 224
TAMANHO_CELULA_ADVERSARIO = 18
INTERVALO_QUEDA = 0.6
DURACAO_ANIMACAO = 0.4  # Segundos: brilho inicial e encolhimento dos blocos.
PONTOS_POR_LINHAS = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
CORES = {
    "LIXO": (130, 130, 130),
    "I": (70, 210, 230),
    "O": (240, 210, 70),
    "T": (180, 80, 220),
    "S": (90, 200, 100),
    "Z": (230, 80, 80),
    "J": (80, 110, 230),
    "L": (240, 150, 60),
}
TITULO = "Tetris | Z: girar | Baixo: descer | R: reiniciar"


def nova_peca(tabuleiro: Tabuleiro, gerador: GeradorPecas) -> Peca:
    return Peca(gerador.proximo_tipo(), x=tabuleiro.largura // 2 - 2)


def desenhar_bloco(tela, tipo: str, x: int, y: int, progresso: float | None = None):
    retangulo = pygame.Rect(
        x * TAMANHO_CELULA, y * TAMANHO_CELULA,
        TAMANHO_CELULA, TAMANHO_CELULA,
    )
    retangulo = retangulo.inflate(-2, -2)
    cor = CORES[tipo]
    if progresso is not None:
        progresso = max(0.0, min(1.0, progresso))
        if progresso < 0.25:
            cor = (255, 255, 255)
        else:
            restante = (1.0 - progresso) / 0.75
            lado = round(retangulo.width * restante)
            if lado <= 0:
                return
            retangulo = pygame.Rect(0, 0, lado, lado)
            retangulo.center = (
                x * TAMANHO_CELULA + TAMANHO_CELULA // 2,
                y * TAMANHO_CELULA + TAMANHO_CELULA // 2,
            )
            cor = tuple(round(18 + (canal - 18) * restante) for canal in cor)
    pygame.draw.rect(tela, cor, retangulo)


def desenhar(
    tela, tabuleiro: Tabuleiro, peca: Peca | None, fim_de_jogo: bool,
    linhas_animadas: list[int] | None = None, progresso: float = 0.0,
):
    tela.fill((18, 18, 25))
    linhas_animadas = set(linhas_animadas or [])
    for y, linha in enumerate(tabuleiro.grade):
        for x, tipo in enumerate(linha):
            pygame.draw.rect(
                tela, (40, 40, 50),
                (x * TAMANHO_CELULA, y * TAMANHO_CELULA,
                 TAMANHO_CELULA, TAMANHO_CELULA),
                width=1,
            )
            if tipo is not None:
                efeito = progresso if y in linhas_animadas else None
                desenhar_bloco(tela, tipo, x, y, efeito)
    if not fim_de_jogo and peca is not None:
        for x, y in peca.celulas():
            desenhar_bloco(tela, peca.tipo, x, y)


def desenhar_placar(tela, pontos: int, fonte):
    """Cabeçalho fora da área de jogo, com o placar no canto esquerdo."""
    pygame.draw.rect(tela, (25, 28, 40), (0, 0, tela.get_width(), ALTURA_CABECALHO))
    texto = fonte.render(f"Pontos: {pontos}", True, (240, 240, 250))
    tela.blit(texto, (10, 8))


def desenhar_adversario(tela, grade, pontos, origem_x, fonte, pequena, recebido):
    """Desenha apenas os blocos fixos do outro jogador, sem peça em movimento."""
    pygame.draw.rect(tela, (22, 24, 34),
                     (origem_x, 0, LARGURA_PAINEL_ADVERSARIO, tela.get_height()))
    pygame.draw.line(tela, (65, 75, 95), (origem_x, 0), (origem_x, tela.get_height()))
    tela.blit(fonte.render("ADVERSÁRIO", True, (100, 230, 160)), (origem_x + 22, 18))
    tela.blit(pequena.render(f"Pontos: {pontos}", True, (235, 235, 245)),
              (origem_x + 22, 54))
    tamanho = TAMANHO_CELULA_ADVERSARIO
    for y, linha in enumerate(grade):
        for x, tipo in enumerate(linha):
            ret = pygame.Rect(origem_x + 22 + x * tamanho, 100 + y * tamanho,
                              tamanho, tamanho)
            pygame.draw.rect(tela, (40, 40, 50), ret, width=1)
            if tipo is not None:
                pygame.draw.rect(tela, CORES[tipo], ret.inflate(-2, -2))
    legenda = "Blocos fixos do adversário" if recebido else "Aguardando atualização..."
    tela.blit(pequena.render(legenda, True, (155, 165, 185)), (origem_x + 22, 482))


def desenhar_resultado(tela, venceu: bool, fonte_titulo, fonte_detalhe,
                      instrucao="R para reiniciar", desconectado=False, detalhe_revanche=None):
    """Painel persistente no centro da tela, sobre o tabuleiro escurecido."""
    sombra = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    sombra.fill((0, 0, 0, 175))
    tela.blit(sombra, (0, 0))

    destaque = (100, 230, 160) if venceu else (255, 115, 115)
    painel = pygame.Rect(0, 0, min(tela.get_width() - 32, 360), 184)
    painel.center = tela.get_rect().center
    pygame.draw.rect(tela, (25, 28, 40), painel, border_radius=14)
    pygame.draw.rect(tela, destaque, painel, width=2, border_radius=14)

    titulo = "VITÓRIA!" if venceu else "GAME OVER"
    detalhe = "Você venceu a partida." if venceu else "Fim de jogo."
    if desconectado:
        titulo = "SESSÃO ENCERRADA"
        detalhe = "A conexão foi interrompida."
    elif detalhe_revanche:
        detalhe = detalhe_revanche
    for texto, fonte, cor, deslocamento in (
        (titulo, fonte_titulo, destaque, -38),
        (detalhe, fonte_detalhe, (235, 235, 245), 8),
        (instrucao, fonte_detalhe, (165, 175, 195), 52),
    ):
        imagem = fonte.render(texto, True, cor)
        if imagem.get_width() > painel.width - 24:
            escala = (painel.width - 24) / imagem.get_width()
            imagem = pygame.transform.smoothscale(
                imagem, (painel.width - 24, round(imagem.get_height() * escala)),
            )
        tela.blit(imagem, imagem.get_rect(
            center=(painel.centerx, painel.centery + deslocamento),
        ))


def main(seed: int | None = None, fila_entrada: Queue | None = None,
         fila_saida: Queue | None = None, partida: int = 1):
    """Roda o jogo e consulta eventos recebidos pela thread de rede."""
    gerador = GeradorPecas(gerar_seed() if seed is None else seed)
    pygame.init()
    multiplayer = fila_saida is not None
    titulo_controles = TITULO.replace("R: reiniciar", "Esc: menu") if multiplayer else TITULO
    tabuleiro = Tabuleiro()
    largura_tabuleiro = tabuleiro.largura * TAMANHO_CELULA
    tela = pygame.display.set_mode((
        largura_tabuleiro + (LARGURA_PAINEL_ADVERSARIO if multiplayer else 0),
        tabuleiro.altura * TAMANHO_CELULA + ALTURA_CABECALHO,
    ))
    area_tabuleiro = tela.subsurface(pygame.Rect(
        0, ALTURA_CABECALHO,
        tabuleiro.largura * TAMANHO_CELULA, tabuleiro.altura * TAMANHO_CELULA,
    ))
    pygame.display.set_caption(f"{titulo_controles} | Seed: {gerador.seed}")
    pygame.key.set_repeat(180, 70)
    relogio = pygame.time.Clock()
    peca = nova_peca(tabuleiro, gerador)
    acumulador_queda = 0.0
    fim_de_jogo = False
    venceu = False
    executando = True
    voltar_menu = False
    desconectado = False
    linhas_animadas = []
    tempo_animacao = 0.0
    fonte_aviso = pygame.font.Font(None, 22)
    fonte_resultado = pygame.font.Font(None, 44)
    fonte_placar = pygame.font.Font(None, 28)
    pontos = 0
    mensagem_rede = ""
    tempo_aviso = 0.0
    linhas_ataque_pendentes = 0
    tabuleiro_adversario = [[None] * tabuleiro.largura for _ in range(tabuleiro.altura)]
    pontos_adversario = 0
    estado_adversario_recebido = False
    revanche_solicitada = False
    adversario_pediu_revanche = False
    conexao_ativa = multiplayer

    def publicar_estado():
        if fila_saida is not None:
            # Uma cópia evita alterações enquanto a thread aguarda para enviar.
            fila_saida.put({
                "tipo": "estado_tabuleiro",
                "tabuleiro": [linha[:] for linha in tabuleiro.grade],
                "pontos": pontos,
                "partida": partida,
            })

    def reiniciar_partida(nova_seed, numero_partida):
        nonlocal gerador, tabuleiro, peca, partida, fim_de_jogo, venceu, desconectado
        nonlocal linhas_ataque_pendentes, pontos, tempo_aviso, mensagem_rede
        nonlocal acumulador_queda, linhas_animadas, tempo_animacao
        nonlocal tabuleiro_adversario, pontos_adversario, estado_adversario_recebido
        nonlocal revanche_solicitada, adversario_pediu_revanche
        partida = numero_partida
        gerador = GeradorPecas(nova_seed)
        tabuleiro = Tabuleiro()
        peca = nova_peca(tabuleiro, gerador)
        fim_de_jogo = venceu = desconectado = False
        linhas_ataque_pendentes = pontos = 0
        tempo_aviso = acumulador_queda = tempo_animacao = 0.0
        mensagem_rede = ""
        linhas_animadas = []
        tabuleiro_adversario = [[None] * tabuleiro.largura for _ in range(tabuleiro.altura)]
        pontos_adversario = 0
        estado_adversario_recebido = False
        revanche_solicitada = adversario_pediu_revanche = False
        pygame.display.set_caption(f"{titulo_controles} | Seed: {gerador.seed}")
        publicar_estado()

    def iniciar_peca():
        nonlocal peca, fim_de_jogo, linhas_ataque_pendentes, fila_saida
        # Só verifica o fim de jogo após remover as linhas completas.
        transbordou = tabuleiro.adicionar_lixo(linhas_ataque_pendentes)
        linhas_ataque_pendentes = 0
        # Linhas e pontos já foram resolvidos; o lixo também já foi aplicado.
        publicar_estado()

        if transbordou:
            fim_de_jogo = True
            peca = None
        else:
            peca = nova_peca(tabuleiro, gerador)
            fim_de_jogo = not tabuleiro.pode_posicionar(peca)

        if fim_de_jogo:
            if fila_saida is not None:
                fila_saida.put({
                    "tipo": "fim_de_jogo", "partida": partida,
                    }
                )
            pygame.display.set_caption(f"Fim de jogo | Seed: {gerador.seed}")

    def descer():
        nonlocal peca, linhas_animadas, tempo_animacao, acumulador_queda
        if peca is None:
            return
        if not tabuleiro.mover(peca, dy=1):
            tabuleiro.fixar(peca)
            acumulador_queda = 0.0
            linhas_animadas = tabuleiro.linhas_completas()
            if linhas_animadas:
                peca = None
                tempo_animacao = 0.0
            else:
                iniciar_peca()

    publicar_estado()  # Estado inicial, sem incluir a peça ativa.
    try:
        while executando:
            dt = relogio.tick(60) / 1000
            tempo_aviso = max(0.0, tempo_aviso - dt)
            if fila_entrada is not None:
                # get_nowait nunca espera: fila vazia significa continuar jogando.
                while True:
                    try:
                        mensagem = fila_entrada.get_nowait()
                    except Empty:
                        break
                    if mensagem.get("tipo") == "inicio":
                        numero = mensagem.get("partida")
                        if (multiplayer and conexao_ativa and fim_de_jogo
                                and type(mensagem.get("seed")) is int
                                and type(numero) is int and numero > partida):
                            reiniciar_partida(mensagem["seed"], numero)
                    elif mensagem.get("tipo") == "revanche_pendente":
                        if fim_de_jogo and mensagem.get("partida") == partida:
                            revanche_solicitada = bool(mensagem.get("voce_confirmou"))
                            adversario_pediu_revanche = not revanche_solicitada
                    elif mensagem.get("tipo") == "estado_tabuleiro":
                        if validar_estado_tabuleiro(mensagem):
                            tabuleiro_adversario = [linha[:] for linha in mensagem["tabuleiro"]]
                            pontos_adversario = mensagem["pontos"]
                            estado_adversario_recebido = True
                    elif mensagem.get("tipo") == "receber_lixo":
                        quantidade = mensagem["quantidade"]
                        mensagem_rede = f"Recebeu um ataque de {quantidade-1} linhas!"
                        linhas_ataque_pendentes += quantidade
                        tempo_aviso = 5.0
                        print(f"[Jogo recebeu pela fila] ataque de {quantidade} linhas.")
                    elif mensagem.get("tipo") == "vencedor":
                        venceu = True
                        fim_de_jogo = True
                        linhas_animadas = []
                        publicar_estado()
                        pygame.display.set_caption("Você venceu!")
                    elif mensagem.get("tipo") in ("conexao_encerrada", "erro_rede",
                                                   "adversario_desconectado"):
                        conexao_ativa = False
                        if not fim_de_jogo:
                            fim_de_jogo = True
                            desconectado = True
                            linhas_animadas = []
                        print(f"[Rede] {mensagem.get('texto', 'Sessão encerrada.')}")

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    executando = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        voltar_menu = True
                        executando = False
                    elif evento.key == pygame.K_r and multiplayer and fim_de_jogo:
                        if conexao_ativa and not revanche_solicitada:
                            revanche_solicitada = True
                            fila_saida.put({"tipo": "reinicio", "partida": partida})

                    elif evento.key == pygame.K_r and not multiplayer:
                        reiniciar_partida(gerar_seed(), partida + 1)
                    elif not fim_de_jogo and peca is not None:
                        if evento.key == pygame.K_LEFT:
                            tabuleiro.mover(peca, dx=-1)
                        elif evento.key == pygame.K_RIGHT:
                            tabuleiro.mover(peca, dx=1)
                        elif evento.key == pygame.K_z:
                            tabuleiro.girar(peca)
                        elif evento.key == pygame.K_DOWN:
                            descer()
                            acumulador_queda = 0.0

            if linhas_animadas:
                tempo_animacao += dt
                if tempo_animacao >= DURACAO_ANIMACAO:
                    quantidade  = tabuleiro.remover_linhas_completas()
                    pontos += PONTOS_POR_LINHAS[quantidade]

                    if quantidade > 1 and fila_saida is not None:
                        fila_saida.put(
                            {
                                 "tipo": "linhas_completadas",
                                "quantidade": quantidade, "partida": partida,
                            }
                        )

                    linhas_animadas = []
                    tempo_animacao = 0.0
                    acumulador_queda = 0.0
                    iniciar_peca()
            elif not fim_de_jogo:
                acumulador_queda += dt
                while (acumulador_queda >= INTERVALO_QUEDA
                       and not fim_de_jogo and not linhas_animadas):
                    acumulador_queda -= INTERVALO_QUEDA
                    descer()

            desenhar(
                area_tabuleiro, tabuleiro, peca, fim_de_jogo,
                linhas_animadas, tempo_animacao / DURACAO_ANIMACAO,
            )
            desenhar_placar(tela, pontos, fonte_placar)
            if multiplayer:
                desenhar_adversario(tela, tabuleiro_adversario, pontos_adversario,
                                    largura_tabuleiro, fonte_placar, fonte_aviso,
                                    estado_adversario_recebido)
            if fim_de_jogo:
                detalhe_revanche = None
                instrucao = "R para reiniciar"
                if multiplayer:
                    instrucao = "R: revanche | Esc: sair"
                    if not conexao_ativa:
                        instrucao = "Esc para voltar"
                    elif revanche_solicitada:
                        detalhe_revanche = "Aguardando o adversário..."
                        instrucao = "Esc para sair"
                    elif adversario_pediu_revanche:
                        detalhe_revanche = "O adversário quer revanche!"
                desenhar_resultado(tela, venceu, fonte_resultado, fonte_aviso,
                                  instrucao=instrucao, desconectado=desconectado,
                                  detalhe_revanche=detalhe_revanche)
            elif tempo_aviso > 0:
                pygame.draw.rect(tela, (30, 50, 70), (0, 32, largura_tabuleiro, 32))
                texto = fonte_aviso.render(mensagem_rede, True, (255, 255, 255))
                tela.blit(texto, texto.get_rect(center=(largura_tabuleiro // 2, 48)))

            pygame.display.flip()
    finally:
        pygame.quit()
    return voltar_menu


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Tetris com sequência de peças por seed.")
    argumentos.add_argument("--seed", type=int, default=None,
                            help="Seed compartilhada da partida; omitida, gera uma automaticamente.")
    args = argumentos.parse_args()
    if args.seed is None:
        from menu import main as abrir_menu
        abrir_menu()
    else:
        main(seed=args.seed)
