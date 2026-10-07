import socket
from queue import Empty, Queue
from threading import Event, Thread

from gerador_pecas import gerar_seed
from sockets.protocolo import enviar_mensagem, LeitorMensagens, receber_mensagem

HOST = "0.0.0.0"
PORT = 6000

class ServidorSessao:
    """Servidor de uma partida, com início e encerramento controlados pelo menu."""

    def __init__(self, host=HOST, porta=PORT):
        self.host = host
        self.porta = porta
        self.parar = Event()
        self.clientes = []
        self.listener = None
        self.thread = Thread(target=self._executar, name="servidor-sessao", daemon=True)

    def iniciar(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind((self.host, self.porta))
            listener.listen(2)
            listener.settimeout(0.2)
        except OSError:
            listener.close()
            raise
        self.listener = listener
        self.porta = listener.getsockname()[1]
        self.thread.start()

    def _receber(self, indice, conexao, eventos):
        leitor = LeitorMensagens(conexao)
        leitor.parar = self.parar
        try:
            while not self.parar.is_set():
                mensagem = receber_mensagem(leitor)
                if mensagem is None:
                    break
                eventos.put((indice, mensagem))
        except (OSError, ValueError):
            pass
        finally:
            eventos.put((indice, {"tipo": "desconectado"}))

    def _executar(self):
        recebimentos = []
        try:
            while len(self.clientes) < 2 and not self.parar.is_set():
                try:
                    conexao, _ = self.listener.accept()
                except socket.timeout:
                    continue
                conexao.settimeout(2)
                self.clientes.append(conexao)
            if self.parar.is_set():
                return

            seed = gerar_seed()
            for cliente in self.clientes:
                enviar_mensagem(cliente, {"tipo": "inicio", "seed": seed})
            eventos = Queue()
            for indice, cliente in enumerate(self.clientes):
                thread = Thread(target=self._receber, args=(indice, cliente, eventos),
                                name=f"servidor-jogador-{indice + 1}", daemon=True)
                thread.start()
                recebimentos.append(thread)

            finalizada = False
            # Só esta thread envia mensagens, evitando escritas concorrentes.
            while not self.parar.is_set():
                try:
                    origem, mensagem = eventos.get(timeout=0.2)
                except Empty:
                    continue
                adversario = self.clientes[1 - origem]
                tipo = mensagem.get("tipo")
                if tipo == "desconectado":
                    enviar_mensagem(adversario, {"tipo": "adversario_desconectado"})
                    return
                if finalizada:
                    continue
                if tipo == "linhas_completadas":
                    quantidade = mensagem.get("quantidade")
                    if type(quantidade) is int and 1 <= quantidade <= 4:
                        enviar_mensagem(adversario, {"tipo": "receber_lixo",
                                                     "quantidade": quantidade})
                elif tipo == "fim_de_jogo":
                    enviar_mensagem(adversario, {"tipo": "vencedor"})
                    finalizada = True
        except OSError:
            pass
        finally:
            self.parar.set()
            self._fechar_sockets()
            for thread in recebimentos:
                thread.join(timeout=1)

    def _fechar_sockets(self):
        if self.listener is not None:
            self.listener.close()
        for cliente in list(self.clientes):
            try:
                cliente.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            cliente.close()

    def encerrar(self):
        self.parar.set()
        self._fechar_sockets()
        if self.thread.ident is not None:
            self.thread.join(timeout=3)


def main():
    servidor = ServidorSessao()
    servidor.iniciar()
    print(f"Servidor aguardando dois jogadores na porta {servidor.porta}.")
    try:
        while servidor.thread.is_alive():
            servidor.thread.join(timeout=0.5)
    finally:
        servidor.encerrar()

if __name__ == "__main__":
    main()
