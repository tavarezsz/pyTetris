"""Sequência de peças reproduzível a partir da seed de uma partida."""

import random
import secrets


# A ordem precisa ser a mesma em todos os clientes.
TIPOS_PECAS = ("I", "O", "T", "S", "Z", "J", "L")


def gerar_seed() -> int:
    """Gera uma seed inteira que pode ser enviada em uma mensagem JSON."""
    return secrets.randbits(32)


class GeradorPecas:
    def __init__(self, seed: int):
        if type(seed) is not int:
            raise TypeError("A seed deve ser um número inteiro.")
        self.seed = seed
        # Instância exclusiva: outros sorteios não afetam a ordem das peças.
        self._random = random.Random(seed)

    def proximo_tipo(self) -> str:
        """Consome exatamente um item da sequência desta partida."""
        return self._random.choice(TIPOS_PECAS)
