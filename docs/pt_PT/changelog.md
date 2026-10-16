# Changelog do plugin Midea MSmart

>**IMPORTANT**
>
>Se não houver informação sobre a atualização, significa que esta diz respeito apenas à atualização da documentação, da tradução ou do texto.

# 16/10/2026

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
