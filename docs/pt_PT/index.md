# Plugin Midea MSmart

> **Plugin em desenvolvimento**: esta documentação descreve o estado atual do plugin e será completada a cada versão.

## Apresentação

O plugin **Midea MSmart** permite controlar **localmente** os aparelhos de ar condicionado e desumidificadores Midea e de marcas associadas (Comfee, Inventor, Qlima…) compatíveis com a aplicação **MSmartHome**.

A conta MSmartHome serve apenas para:

- listar os aparelhos associados à conta;
- obter uma única vez as chaves de autenticação (*token* e *key*) dos aparelhos recentes (protocolo V3).

Depois disso, todos os comandos e leituras de estado passam diretamente pela rede local, sem a nuvem da Midea.

Aparelhos suportados:

| Tipo | Aparelho |
|---|---|
| `0xAC` | Ar condicionado (split, portátil, PortaSplit…) |
| `0xCC` | Ar condicionado comercial |
| `0xA1` | Desumidificador |

## Pré-requisitos

- Jeedom 4.5 ou superior, em Debian 12 ou 13.
- Os aparelhos e o Jeedom devem estar na **mesma rede local** (mesma sub-rede) para que a deteção funcione.
- Uma conta **MSmartHome** na qual os aparelhos estejam **emparelhados diretamente**. Um aparelho apenas *partilhado* a partir de outra conta não permite obter as suas chaves.

> **Conselho**
>
> Use de preferência uma palavra-passe composta apenas por letras e algarismos.
> Após várias tentativas de ligação falhadas, a nuvem da Midea bloqueia temporariamente a conta, de alguns minutos até 24 horas (erros `7610` ou `65027`). Nesse caso, aguarde antes de tentar novamente.

## Configuração do plugin

Após a instalação, ative o plugin e inicie a instalação das dependências. O plugin instala o seu próprio ambiente Python, isolado do sistema.

### Dependências

A instalação das dependências, iniciada a partir da página de configuração do plugin, instala apenas na pasta do plugin:

- um **Python 3.13** autónomo, descarregado com a ferramenta [uv](https://github.com/astral-sh/uv), independentemente da versão de Python do sistema;
- um ambiente virtual (`resources/python_venv`) com as bibliotecas do plugin, em versões fixas e verificadas por impressão digital.

A instalação demora alguns minutos e ocupa cerca de 130 MB. Num sistema de 32 bits (Raspberry Pi em `armhf`), é também instalado um compilador e a operação é mais demorada, pois uma biblioteca tem de ser compilada.

Após uma atualização do plugin que altere estas versões, as dependências voltam ao estado *NOK*: basta relançar a sua instalação. Não são incluídas nas cópias de segurança do Jeedom; após um restauro, relance a sua instalação.

### Parâmetros

![Configuração do plugin](../images/plugin_config.png)

- **Conta MSmartHome**
  - **Utilizador (email)** e **Palavra-passe** da conta MSmartHome.
- **Rede local**
  - **Endereço de difusão**: endereço(s) de broadcast usado(s) para descobrir os aparelhos, separados por vírgulas. O valor predefinido `255.255.255.255` serve na maioria dos casos. Se os aparelhos não forem encontrados, indique o endereço de broadcast da sua rede (por exemplo `192.168.1.255`).
  - **Intervalo de consulta predefinido**: tempo em segundos entre duas leituras do estado dos aparelhos (30 s por predefinição, 10 s no mínimo).
- **Daemon**
  - **Porta do daemon**: porta local usada pelo daemon (55114 por predefinição). Altere-a apenas em caso de conflito com outro plugin.

## Adicionar aparelhos

Na página do plugin, o botão **Sincronizar** obtém os aparelhos da conta MSmartHome, procura-os na rede local e cria os equipamentos correspondentes.

![Página do plugin](../images/plugin_devices.png)

O botão **Adicionar** permite criar um equipamento manualmente, por exemplo para um aparelho situado noutra sub-rede. Nesse caso, terá de indicar o identificador, o endereço IP e, para um aparelho V3, o *token* e a *key*.

## Equipamento

![Equipamento](../images/device_config.png)

- **Aparelho Midea**
  - **Tipo de aparelho**: ar condicionado, ar condicionado comercial ou desumidificador.
  - **Identificador do aparelho**: identificador Midea, preenchido automaticamente durante a sincronização.
- **Ligação local**
  - **Endereço IP** e **Porta** (6444 por predefinição).
  - **Versão do protocolo**: V3 para a maioria dos aparelhos recentes, V2 para os mais antigos.
  - **Token** e **Key**: chaves de autenticação dos aparelhos V3, obtidas automaticamente.
- **Opções**
  - **Intervalo de consulta**: deixe vazio para usar o valor da configuração do plugin.
- **Informações**
  - Número de série e modelo do aparelho, apenas de leitura.

> **Importante**
>
> Guarde o *token* e a *key* dos seus aparelhos V3 num local seguro. Permitem continuar a controlar os aparelhos mesmo que a nuvem da Midea fique indisponível.

## Comandos

Os comandos são criados automaticamente de acordo com as capacidades comunicadas por cada aparelho. A sua lista detalhada será adicionada aqui assim que estiverem disponíveis.

## Créditos

O plugin baseia-se nas bibliotecas de código aberto [msmart-ng](https://github.com/mill1000/midea-msmart) e [midea-local](https://github.com/midea-lan/midea-local).
