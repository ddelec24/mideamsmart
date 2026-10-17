# Changelog do plugin Midea MSmart

>**IMPORTANT**
>
>Se não houver informação sobre a atualização, significa que esta diz respeito apenas à atualização da documentação, da tradução ou do texto.

# 17/10/2026

- Versão beta 0.9.1
- Créditos: autores do plugin indicados (ddelec24, maestro; Claude, coautor) na documentação, na licença e na ficha do plugin
- Nova opção **Duração das ligações** (90 s por predefinição), solução para os aparelhos que cortam eles próprios a ligação (erros *Transport is closing or closed* e *failed CRC and checksum*)
- Pedido ou comando reenviado uma vez numa nova ligação quando o aparelho corta a ligação, e aparelho declarado offline apenas após duas falhas seguidas
- Estes erros da biblioteca são registados como warning
- Capacidades pedidas de novo rapidamente se o aparelho não as enviou, com ajuste automático dos comandos ao recebê-las (comandos a mais, como *Filtro a limpar*, num só aparelho)
- Indicador do estado das capacidades na página do equipamento
- Correção de um erro ao parar um desumidificador

# 16/10/2026

- Primeira versão beta (0.9.0), a testar com aparelhos reais: os seus comentários são bem-vindos no fórum
- Criação do plugin: estrutura de base, página de configuração e página dos equipamentos
- Instalação das dependências: Python 3.13 autónomo (via uv) e ambiente virtual dedicado ao plugin
- Daemon Python (asyncio): arranque, paragem limpa, comunicação com o Jeedom e transmissão da lista de equipamentos
- Sincronização dos aparelhos: conta MSmartHome, procura na rede local, criação e atualização dos equipamentos
- Obtenção do token e da key, verificados junto do aparelho, e botão para os voltar a pedir
- Proteção contra o bloqueio da conta Midea (códigos 7610 e 65027)
- Endereço de difusão automático por predefinição (todas as interfaces de rede)
- Controlo local dos aparelhos de ar condicionado (AC) e ar condicionado comercial (CC) com msmart-ng: estado, consulta periódica, aparelho offline
- Comandos criados de acordo com as capacidades de cada aparelho, com códigos estáveis para os cenários e botão de atualização
- Opções do equipamento: bip, passo da temperatura definida, consumo elétrico
- Controlo local dos desumidificadores (A1) com midea-local: modo, ventilação, humidade definida, depósito, oscilação, ionizador, bomba, bloqueio para crianças, filtro
- Alertas de depósito cheio e de filtro apresentados com um ícone verde ou vermelho
- Janela de diagnóstico por equipamento, com cópia de um resumo sem segredos para o fórum
- Procura automática na rede local dos aparelhos que mudaram de endereço IP
- Bloqueios da nuvem e palavra-passe recusada memorizados, mesmo após reinício do daemon
- Equipamento assinalado em timeout quando o aparelho deixa de responder, página Saúde e informações para o fórum
