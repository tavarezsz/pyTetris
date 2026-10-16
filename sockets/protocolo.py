"""Uma mensagem JSON por linha, para separar mensagens no fluxo TCP."""

import json
import socket
import select
from threading import Event
from typing import TextIO


def validar_estado_tabuleiro(mensagem: dict) -> bool:
    """Verifica o formato do estado que será desenhado pelo adversário."""
    grade = mensagem.get("tabuleiro")
    pontos = mensagem.get("pontos")
    tipos = {"I", "O", "T", "S", "Z", "J", "L", "LIXO"}
    return (
        type(pontos) is int and pontos >= 0
        and isinstance(grade, list) and len(grade) == 20
        and all(
            isinstance(linha, list) and len(linha) == 10
            and all(celula is None or (isinstance(celula, str) and celula in tipos)
                    for celula in linha)
            for linha in grade
        )
    )


def enviar_mensagem(conexao: socket.socket, mensagem: dict) -> None:
    dados = json.dumps(mensagem, ensure_ascii=False) + "\n"
    conexao.sendall(dados.encode("utf-8"))


class LeitorMensagens:
    """Acumula bytes de mensagens e permite interromper a espera pela rede."""

    def __init__(self, conexao: socket.socket):
        self.conexao = conexao
        self.parar = Event()
        self._buffer = b""

    def readline(self) -> str:
        while not self.parar.is_set():
            if b"\n" in self._buffer:
                linha, self._buffer = self._buffer.split(b"\n", 1)
                return (linha + b"\n").decode("utf-8")
            # A espera curta ocorre só na thread de rede e permite verificar parar.
            prontos, _, _ = select.select([self.conexao], [], [], 0.1)
            if not prontos:
                continue
            dados = self.conexao.recv(4096)
            if not dados:
                linha, self._buffer = self._buffer, b""
                return linha.decode("utf-8")
            self._buffer += dados
        return ""


def receber_mensagem(leitor: TextIO | LeitorMensagens) -> dict | None:
    # readline acumula os bytes até uma mensagem inteira chegar.
    linha = leitor.readline()
    if not linha:
        return None  # O outro lado fechou a conexão.
    if not linha.endswith("\n"):
        raise ValueError("Conexão encerrada no meio de uma mensagem.")
    mensagem = json.loads(linha)
    if not isinstance(mensagem, dict):
        raise ValueError("A mensagem precisa ser um objeto JSON.")
    return mensagem
