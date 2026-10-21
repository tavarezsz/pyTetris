import socket
from queue import Empty, Queue
from threading import Event, Thread

from gerador_pecas import gerar_seed
from sockets.protocolo import (
    enviar_mensagem, LeitorMensagens, receber_mensagem, validar_estado_tabuleiro,
)

HOST = "0.0.0.0"
PORT = 6000

class ServidorSessao:
    """Servidor de uma partida, com início e encerramento controlados pelo menu."""

    def __init__(self, host=HOST, porta=PORT):
        self.host = host
        self.porta = porta
        self.parar = Event()
        self.encerrado = Event()
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
            partida = 1
            for cliente in self.clientes:
                enviar_mensagem(cliente, {"tipo": "inicio", "seed": seed, "partida": partida})
            eventos = Queue()
            for indice, cliente in enumerate(self.clientes):
                thread = Thread(target=self._receber, args=(indice, cliente, eventos),
                                name=f"servidor-jogador-{indice + 1}", daemon=True)
                thread.start()
                recebimentos.append(thread)

            finalizada = False
            pedidos_reinicio = set()
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
                # Eventos atrasados de uma partida anterior não afetam a revanche.
                if mensagem.get("partida", partida) != partida:
                    continue
                if tipo == "reinicio":
                    if not finalizada or origem in pedidos_reinicio:
                        continue
                    pedidos_reinicio.add(origem)
                    if len(pedidos_reinicio) == 2:
                        seed = gerar_seed()
                        partida += 1
                        finalizada = False
                        pedidos_reinicio.clear()
                        for cliente in self.clientes:
                            enviar_mensagem(cliente, {
                                "tipo": "inicio", "seed": seed, "partida": partida,
                            })
                    else:
                        for indice, cliente in enumerate(self.clientes):
                            enviar_mensagem(cliente, {
                                "tipo": "revanche_pendente", "partida": partida,
                                "voce_confirmou": indice in pedidos_reinicio,
                            })
                    continue
                if tipo == "estado_tabuleiro":
                    if validar_estado_tabuleiro(mensagem):
                        enviar_mensagem(adversario, {
                            "tipo": "estado_tabuleiro", "tabuleiro": mensagem["tabuleiro"],
                            "pontos": mensagem["pontos"],
                        })
                    # O estado final também pode chegar depois do resultado.
                    continue
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
            for thread in recebimentos:
                thread.join(timeout=1)
            try:
                self._fechar_sockets()
            finally:
                self.encerrado.set()

    def _fechar_sockets(self):
        if self.listener is not None:
            self.listener.close()
        for cliente in list(self.clientes):
            try:
                cliente.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            cliente.close()

    def encerrar(self, aguardar=True):
        self.parar.set()
        # O accept e a fila já têm timeout. A thread sai e fecha seus sockets,
        # sem competir com a interface durante operações de rede.
        if self.thread.ident is not None:
            if aguardar:
                self.thread.join(timeout=3)
        else:
            self.encerrado.set()


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
