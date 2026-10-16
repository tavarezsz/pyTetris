# Tetris com pygame-ce

Execute `python main.py` para abrir o menu multiplayer.

## Criar e entrar em sessões

No computador host, escolha **Criar sessão**, informe a porta (padrão 6000)
e clique em **Criar e aguardar**. O servidor escuta em `0.0.0.0` e o seu
cliente conecta automaticamente em `127.0.0.1`. Não é preciso abrir um
servidor em outro terminal. A tela mostra um IP local detectado, que pode
variar caso existam múltiplas interfaces de rede.

No computador convidado, escolha **Entrar em sessão**, informe o IP ou nome
do host e a mesma porta. Os dois jogos começam quando ambos estiverem
conectados, usando a mesma seed. Tab troca de campo, Enter confirma e
Esc cancela a espera ou volta ao menu durante a partida.

Para testar tudo no mesmo computador, abra `python main.py` duas vezes:
crie a sessão em uma janela e entre com `127.0.0.1` na outra.

Na mesma rede, o convidado usa o IP local do host. Em redes diferentes,
usa o IP público ou domínio acessível: o host precisa liberar a porta TCP
no firewall e encaminhá-la no roteador. Sob CGNAT, pode ser necessária uma
rede virtual privada ou um servidor com acesso público. O menu não altera
o firewall nem o roteador.

Cancelar ou sair fecha os sockets e o servidor criado por aquela sessão.
Uma desconexão durante o jogo encerra a partida do outro jogador.
Após o resultado, pressione R para confirmar uma revanche. O painel mostra
quem está aguardando e avisa quando o adversário quer jogar novamente.
O servidor espera os dois jogadores confirmarem, gera uma nova seed e envia
`inicio` aos dois, mantendo as mesmas conexões. Tabuleiros, pontos, ataques
pendentes e animações são zerados. Confirmações repetidas contam uma única vez.
Cada partida recebe um número; eventos atrasados da anterior são ignorados.
Esc volta ao menu e encerra a sessão, inclusive durante a espera por revanche.

## Jogo local e sequência por seed

Para jogar localmente ou reproduzir a sequência de uma partida:

```powershell
python main.py --seed 12345
```

Setas esquerda/direita movem, baixo desce, Z gira e R reinicia o jogo local.
A pontuação é 100, 300, 500 ou 800 pontos por remoção de 1, 2, 3 ou 4 linhas.

Cada cliente possui um `GeradorPecas(seed)` independente. Jogadores com
velocidades diferentes recebem os mesmos tipos na mesma ordem. Ambos devem
executar a mesma versão do jogo e do Python. O sorteio dos buracos das linhas
de lixo é independente da sequência das peças.

## Organização da comunicação

`menu.py` desenha a interface e controla a criação/entrada/cancelamento.
`ServidorSessao`, em `sockets/server_tcp.py`, aceita os dois clientes, gera
uma seed e encaminha os ataques e o resultado. `ConexaoCliente`, em
`sockets/client_tcp.py`, conecta em segundo plano e possui filas de entrada
e saída. A thread de rede não chama o Pygame nem modifica o tabuleiro.

No multiplayer, o painel à direita mostra uma miniatura do tabuleiro do
adversário e seus pontos. A mensagem `estado_tabuleiro` envia uma cópia dos
blocos fixos após cada jogada resolvida: remoção de linhas, pontuação e lixo
pendente. Também são enviados os estados inicial e final. A peça em movimento
não é transmitida. O servidor valida o formato e encaminha o estado ao outro
cliente, que substitui sua miniatura pela atualização mais recente.

As mensagens são JSON em UTF-8 terminadas por uma quebra de linha. O leitor
acumula os dados até receber uma mensagem inteira. A espera pela rede pode
ser interrompida para cancelar a sessão sem travar a interface.

Também é possível executar manualmente, a partir da raiz do projeto:

```powershell
python -m sockets.server_tcp
python -m sockets.client_tcp --host 127.0.0.1 --port 6000
```

Nesse caso, abra dois clientes para o servidor iniciar a partida. No PyCharm,
use Module name para esses comandos, com Working directory na raiz do projeto.
Para o menu, execute `main.py` normalmente, com o interpretador da `.venv`.

## Testes

```powershell
python -m unittest discover -v
```
