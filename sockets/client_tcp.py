import socket
import argparse
from queue import Queue
from threading import Event, Thread

from sockets.protocolo import LeitorMensagens, receber_mensagem, enviar_mensagem

HOST = "127.0.0.1"
PORT = 6000

def enviar_eventos(conexao: socket.socket, fila_saida: Queue):
    while True:
        mensagem = fila_saida.get()

        if mensagem is None:
            return
        try:
            enviar_mensagem(conexao, mensagem)
        except OSError:
            return #Conexão encerrada

def receber_eventos(leitor: LeitorMensagens, fila_entrada: Queue) -> None:
    """Roda na thread de rede. Não desenha nem altera o tabuleiro."""
    try:
        while True:
            mensagem = receber_mensagem(leitor)  # Pode esperar sem travar o jogo.
            if mensagem is None:
                fila_entrada.put({"tipo": "conexao_encerrada"})
                return
            fila_entrada.put(mensagem)
    except (OSError, ValueError) as erro:
        fila_entrada.put({"tipo": "erro_rede", "texto": str(erro)})


class ConexaoCliente:
    """Conecta e espera a seed fora da thread que desenha a interface."""

    def __init__(self, host: str, porta: int):
        self.host = host
        self.porta = porta
        self.fila_entrada = Queue()
        self.fila_saida = Queue()
        self.parar = Event()
        self.conexao = None
        self.thread = Thread(target=self._executar, name="cliente-rede", daemon=True)

    def iniciar(self):
        self.thread.start()

    def _executar(self):
        envio = None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexao:
                self.conexao = conexao
                if self.parar.is_set():
                    return
                conexao.settimeout(4)
                conexao.connect((self.host, self.porta))
                if self.parar.is_set():
                    return
                conexao.settimeout(2)
                leitor = LeitorMensagens(conexao)
                leitor.parar = self.parar
                self.fila_entrada.put({"tipo": "aguardando"})
                inicio = receber_mensagem(leitor)
                if self.parar.is_set():
                    return
                if inicio is None or inicio.get("tipo") != "inicio":
                    raise ValueError("O servidor não enviou o início da partida.")
                if type(inicio.get("seed")) is not int:
                    raise ValueError("A seed recebida deve ser um inteiro.")
                envio = Thread(target=enviar_eventos, args=(conexao, self.fila_saida),
                               name="cliente-envio", daemon=True)
                envio.start()
                self.fila_entrada.put(inicio)
                receber_eventos(leitor, self.fila_entrada)
        except (OSError, ValueError) as erro:
            if not self.parar.is_set():
                self.fila_entrada.put({"tipo": "erro_rede", "texto": str(erro)})
        finally:
            self.parar.set()
            self.fila_saida.put(None)
            if envio is not None:
                envio.join(timeout=3)

    def encerrar(self):
        self.parar.set()
        self.fila_saida.put(None)
        if self.conexao is not None:
            try:
                self.conexao.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.conexao.close()
        if self.thread.ident is not None:
            self.thread.join(timeout=0.5)


def main(host=HOST, porta=PORT):
    from main import main as iniciar_jogo

    cliente = ConexaoCliente(host, porta)
    cliente.iniciar()
    try:
        while True:
            mensagem = cliente.fila_entrada.get()
            if mensagem["tipo"] == "aguardando":
                print("Conectado. Aguardando o segundo jogador...")
            elif mensagem["tipo"] == "inicio":
                iniciar_jogo(seed=mensagem["seed"], fila_entrada=cliente.fila_entrada,
                             fila_saida=cliente.fila_saida)
                return
            elif mensagem["tipo"] in ("erro_rede", "conexao_encerrada"):
                raise ConnectionError(mensagem.get("texto", "Conexão encerrada."))
    finally:
        cliente.encerrar()


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--host", default=HOST)
    argumentos.add_argument("--port", type=int, default=PORT)
    args = argumentos.parse_args()
    main(args.host, args.port)
