"""Protótipo: setas movem, Z gira e R reinicia; linhas cheias somem com animação."""

import argparse
from queue import Empty, Queue

import pygame

from gerador_pecas import GeradorPecas, gerar_seed
from pecas import Peca
from tabuleiro import Tabuleiro


TAMANHO_CELULA = 30
ALTURA_CABECALHO = 64
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


def desenhar_resultado(tela, venceu: bool, fonte_titulo, fonte_detalhe,
                      instrucao="R para reiniciar", desconectado=False):
    """Painel persistente no centro da tela, sobre o tabuleiro escurecido."""
    sombra = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    sombra.fill((0, 0, 0, 175))
    tela.blit(sombra, (0, 0))

    destaque = (100, 230, 160) if venceu else (255, 115, 115)
    painel = pygame.Rect(0, 0, tela.get_width() - 32, 184)
    painel.center = tela.get_rect().center
    pygame.draw.rect(tela, (25, 28, 40), painel, border_radius=14)
    pygame.draw.rect(tela, destaque, painel, width=2, border_radius=14)

    titulo = "VITÓRIA!" if venceu else "GAME OVER"
    detalhe = "Você venceu a partida." if venceu else "Fim de jogo."
    if desconectado:
        titulo = "SESSÃO ENCERRADA"
        detalhe = "A conexão foi interrompida."
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


def main(seed: int | None = None, fila_entrada: Queue | None = None, fila_saida: Queue | None = None,):
    """Roda o jogo e consulta eventos recebidos pela thread de rede."""
    gerador = GeradorPecas(gerar_seed() if seed is None else seed)
    pygame.init()
    multiplayer = fila_saida is not None
    titulo_controles = TITULO.replace("R: reiniciar", "Esc: menu") if multiplayer else TITULO
    tabuleiro = Tabuleiro()
    tela = pygame.display.set_mode((
        tabuleiro.largura * TAMANHO_CELULA,
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

    def iniciar_peca():
        nonlocal peca, fim_de_jogo, linhas_ataque_pendentes, fila_saida
        # Só verifica o fim de jogo após remover as linhas completas.
        transbordou = tabuleiro.adicionar_lixo(linhas_ataque_pendentes)
        linhas_ataque_pendentes = 0

        if transbordou:
            fim_de_jogo = True
            peca = None
        else:
            peca = nova_peca(tabuleiro, gerador)
            fim_de_jogo = not tabuleiro.pode_posicionar(peca)

        if fim_de_jogo:
            if fila_saida is not None:
                fila_saida.put({
                    "tipo": "fim_de_jogo"
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
                    if mensagem.get("tipo") == "receber_lixo":
                        quantidade = mensagem["quantidade"]
                        mensagem_rede = f"Recebeu um ataque de {quantidade} linhas!"
                        linhas_ataque_pendentes += quantidade
                        tempo_aviso = 5.0
                        print(f"[Jogo recebeu pela fila] ataque de {quantidade} linhas.")
                    elif mensagem.get("tipo") == "vencedor":
                        venceu = True
                        fim_de_jogo = True
                        linhas_animadas = []
                        pygame.display.set_caption("Você venceu!")
                    elif mensagem.get("tipo") in ("conexao_encerrada", "erro_rede",
                                                   "adversario_desconectado"):
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
                    elif evento.key == pygame.K_r and not multiplayer:
                        # No modo local, R inicia uma nova partida com outra seed.
                        # Com sockets, o servidor coordenará a seed de ambos os clientes.
                        gerador = GeradorPecas(gerar_seed())
                        tabuleiro = Tabuleiro()
                        peca = nova_peca(tabuleiro, gerador)
                        fim_de_jogo = False
                        venceu = False
                        desconectado = False
                        linhas_ataque_pendentes = 0
                        pontos = 0
                        tempo_aviso = 0.0
                        mensagem_rede = ""
                        acumulador_queda = 0.0
                        linhas_animadas = []
                        tempo_animacao = 0.0
                        pygame.display.set_caption(f"{titulo_controles} | Seed: {gerador.seed}")
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

                    if quantidade > 0 and fila_saida is not None:
                        fila_saida.put(
                            {
                                 "tipo": "linhas_completadas",
                                "quantidade": quantidade
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
            if fim_de_jogo:
                desenhar_resultado(tela, venceu, fonte_resultado, fonte_aviso,
                                  instrucao="Esc para voltar" if multiplayer else "R para reiniciar",
                                  desconectado=desconectado)
            elif tempo_aviso > 0:
                pygame.draw.rect(tela, (30, 50, 70), (0, 32, tela.get_width(), 32))
                texto = fonte_aviso.render(mensagem_rede, True, (255, 255, 255))
                tela.blit(texto, texto.get_rect(center=(tela.get_width() // 2, 48)))
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
