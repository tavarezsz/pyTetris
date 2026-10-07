"""Formatos e posições das peças, em células do tabuleiro."""

from dataclasses import dataclass


FORMATOS = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}


def _gerar_rotacoes(tipo: str) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Gira os blocos em uma caixa 3x3 (4x4 para I), no sentido horário."""
    formato = FORMATOS[tipo]
    if tipo == "O":
        return (formato,) * 4
    tamanho = 4 if tipo == "I" else 3
    rotacoes = []
    for _ in range(4):
        rotacoes.append(formato)
        formato = tuple((tamanho - 1 - y, x) for x, y in formato)
    return tuple(rotacoes)


ROTACOES = {tipo: _gerar_rotacoes(tipo) for tipo in FORMATOS}


@dataclass
class Peca:
    tipo: str
    x: int = 3
    y: int = 0
    rotacao: int = 0

    def __post_init__(self):
        if self.tipo not in FORMATOS:
            raise ValueError(f"Tipo de peça desconhecido: {self.tipo}")
        self.rotacao %= 4

    def celulas(self, dx: int = 0, dy: int = 0) -> list[tuple[int, int]]:
        """Retorna posições absolutas, com deslocamento opcional para colisões."""
        formato = ROTACOES[self.tipo][self.rotacao]
        return [(self.x + x + dx, self.y + y + dy) for x, y in formato]
