"""Grade de blocos fixos e colisões, sem dependência do Pygame."""

from dataclasses import replace
import secrets

from pecas import Peca


class Tabuleiro:
    def __init__(self, largura: int = 10, altura: int = 20):
        if largura <= 0 or altura <= 0:
            raise ValueError("As dimensões do tabuleiro devem ser positivas.")
        self.largura = largura
        self.altura = altura
        self.grade: list[list[str | None]] = [
            [None for _ in range(largura)] for _ in range(altura)
        ]

    def pode_posicionar(self, peca: Peca, dx: int = 0, dy: int = 0) -> bool:
        for x, y in peca.celulas(dx, dy):
            if not (0 <= x < self.largura and 0 <= y < self.altura):
                return False
            if self.grade[y][x] is not None:
                return False
        return True

    def mover(self, peca: Peca, dx: int = 0, dy: int = 0) -> bool:
        if not self.pode_posicionar(peca, dx, dy):
            return False
        peca.x += dx
        peca.y += dy
        return True

    def fixar(self, peca: Peca) -> None:
        """Copia a peça ativa para a grade quando ela termina de cair."""
        if not self.pode_posicionar(peca):
            raise ValueError("Não é possível fixar a peça nessa posição.")
        for x, y in peca.celulas():
            self.grade[y][x] = peca.tipo

    def linhas_completas(self) -> list[int]:
        """Retorna os índices das linhas cheias sem alterar a grade."""
        return [
            y for y, linha in enumerate(self.grade)
            if all(celula is not None for celula in linha)
        ]

    def remover_linhas_completas(self) -> int:
        """Remove todas as linhas cheias de uma vez e repõe vazias no topo.

        O retorno será útil para enviar ataques ao adversário futuramente.
        """
        completas = set(self.linhas_completas())
        if not completas:
            return 0
        restantes = [linha for y, linha in enumerate(self.grade) if y not in completas]
        vazias = [[None for _ in range(self.largura)] for _ in completas]
        self.grade = vazias + restantes
        return len(completas)

    def adicionar_lixo(self, quantidade: int) -> bool:
        """Insere linhas de ataque no fundo, com um buraco sorteado por linha.

        Empurra os blocos fixos para cima, mantendo a altura do tabuleiro.
        Retorna True se algum bloco foi expulso pelo topo (derrota).
        Não move a peça ativa; chame antes de criar a próxima peça.
        """


        if type(quantidade) is not int:
            raise TypeError("A quantidade de linhas deve ser um inteiro.")
        if quantidade < 0:
            raise ValueError("A quantidade de linhas não pode ser negativa.")

        if 0 < quantidade < 4:
            quantidade-=1

        transbordou = False
        for _ in range(quantidade):
            if any(celula is not None for celula in self.grade[0]):
                transbordou = True
            linha = ["LIXO"] * self.largura
            # Sorteio independente do gerador de peças da partida.
            linha[secrets.randbelow(self.largura)] = None
            self.grade = self.grade[1:] + [linha]
        return transbordou

    def girar(self, peca: Peca) -> bool:
        """Tenta um giro horário, ajustando até duas células na horizontal.

        A peça original só muda se uma posição válida for encontrada.
        Estes ajustes são simples; não implementam o sistema completo SRS.
        """
        candidata = replace(peca, rotacao=(peca.rotacao + 1) % 4)
        for dx in (0, -1, 1, -2, 2):
            if self.pode_posicionar(candidata, dx=dx):
                peca.rotacao = candidata.rotacao
                peca.x += dx
                return True
        return False
