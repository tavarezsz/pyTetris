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
        self._previa: str | None = None

    def ver_proximo_tipo(self) -> str:
        """Consulta a próxima peça sem retirá-la da sequência."""
        if self._previa is None:
            self._previa = self._random.choice(TIPOS_PECAS)
        return self._previa

    def proximo_tipo(self) -> str:
        """Consome exatamente um item da sequência desta partida."""
        if self._previa is not None:
            tipo = self._previa
            self._previa = None
            return tipo
        return self._random.choice(TIPOS_PECAS)
