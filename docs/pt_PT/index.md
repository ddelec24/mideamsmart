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
  - **Endereço de difusão**: endereço(s) de broadcast usado(s) para descobrir os aparelhos, separados por vírgulas. Deixe vazio (predefinição) para difundir em todas as interfaces de rede do Jeedom. Se os aparelhos não forem encontrados, indique o endereço de broadcast da sua rede (por exemplo `192.168.1.255`).
  - **Intervalo de consulta predefinido**: tempo em segundos entre duas leituras do estado dos aparelhos (30 s por predefinição, 10 s no mínimo).
- **Daemon**
  - **Porta do daemon**: porta local usada pelo daemon (55114 por predefinição). Altere-a apenas em caso de conflito com outro plugin.

### Daemon

O daemon assegura a comunicação local com os aparelhos. Depois de instaladas as dependências, inicia-se automaticamente (gestão automática ativada), ou com o botão **(Re)Iniciar** da página de configuração do plugin.

- Escuta apenas na máquina Jeedom (`127.0.0.1`), na porta definida acima.
- **Nunca** se liga à nuvem da Midea ao iniciar, o que evita os bloqueios da conta.
- As suas mensagens estão no log `mideamsmart_daemon`, as da instalação das dependências em `mideamsmart_update`. Coloque o nível de log do plugin em *Debug* para obter o detalhe das trocas. O plugin oculta neles as palavras-passe, o *token* e a *key*.

## Adicionar aparelhos

Na página do plugin, o botão **Sincronizar** (o daemon deve estar iniciado):

1. procura os aparelhos na rede local;
2. se houver uma conta MSmartHome configurada, liga-se a ela e obtém a lista dos aparelhos da conta;
3. para cada aparelho V3 cujas chaves ainda não são conhecidas, obtém o *token* e a *key* na nuvem e depois **verifica-os diretamente junto do aparelho** antes de os guardar;
4. cria os novos equipamentos, ou atualiza o endereço IP, a porta e o protocolo dos existentes. Os nomes e as chaves já presentes nunca são alterados.

Uma mensagem resume a operação e indica os aparelhos cujas chaves não puderam ser obtidas. Os aparelhos de um tipo não suportado são ignorados. Sem conta MSmartHome, é feita apenas a procura local.

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
  - **Obter token/key a partir da nuvem**: volta a pedir à nuvem as chaves deste aparelho e verifica-as, por exemplo após uma reposição do módulo Wi-Fi. Guarde o equipamento antes de o usar.
- **Opções**
  - **Intervalo de consulta**: deixe vazio para usar o valor da configuração do plugin.
  - **Bip de confirmação**: o aparelho emite um bip a cada comando recebido.
  - **Passo da temperatura definida**: 1 °C ou 0,5 °C.
  - **Consumo elétrico** (ar condicionado): cria os comandos de potência e consumo. Se os valores forem incoerentes, altere o **formato** (BCD ou binário) ou o **fator de escala**.
- **Informações**
  - Número de série e modelo do aparelho, apenas de leitura.

> **Importante**
>
> Guarde o *token* e a *key* dos seus aparelhos V3 num local seguro. Permitem continuar a controlar os aparelhos mesmo que a nuvem da Midea fique indisponível.

## Comandos

Os comandos são criados automaticamente **de acordo com as capacidades comunicadas por cada aparelho**, assim que responde pela primeira vez. Se o aparelho não devolver as suas capacidades, são usadas capacidades predefinidas e o pedido é repetido a cada 10 minutos.

Os comandos info de tipo texto contêm um **código estável**, independente do idioma (por exemplo `cool`): use estes códigos nos seus cenários. Os comandos action associados propõem etiquetas traduzidas. As infos já apresentadas por uma ação ligada ficam ocultas por predefinição.

O botão **Atualizar os comandos** do separador *Comandos* adiciona os comandos em falta, remove os das funções que o aparelho já não declara e volta a ler as suas capacidades. Os nomes e definições dos comandos existentes são mantidos.

| Identificador lógico | Aparelhos | Conteúdo |
|---|---|---|
| `power`, `on`, `off` | AC, CC | Estado (0/1), ligar, desligar |
| `mode`, `setMode` | AC, CC | Modo: `auto`, `cool`, `dry`, `smart_dry`, `heat`, `fan_only` (CC: `fan`). Escolher um modo liga o aparelho |
| `targetTemperature`, `setTargetTemperature` | AC, CC | Temperatura definida em °C, com os limites do aparelho e o passo escolhido no equipamento |
| `indoorTemperature`, `outdoorTemperature` | AC, CC | Temperaturas interior e exterior |
| `fanSpeed`, `setFanSpeed` | AC, CC | Ventilação: `auto`, `silent`, `low`, `medium`, `high`, `max`, `custom` (CC: `l1` a `l7`, `auto`) |
| `fanSpeedPercent`, `setFanSpeedPercent` | AC | Velocidade livre de 1 a 100 %, se o aparelho a suportar |
| `swingMode`, `setSwingMode` | AC, CC | Oscilação: `off`, `vertical`, `horizontal`, `both` |
| `horizontalSwingAngle`, `verticalSwingAngle` + `set…` | AC, CC | Posição das aletas: `off`/`close`, `pos_1` a `pos_5`, `auto` |
| `preset`, `setPreset` | AC, CC | Predefinição exclusiva: `none`, `sleep`, `freeze_protection`, `eco`, `ieco`, `turbo` (CC: `none`, `eco`, `silent`, `sleep`) |
| `breezeMode`, `setBreezeMode` | AC | Modo Breeze: `off`, `breeze_away`, `breeze_mild`, `breezeless` |
| `indoorHumidity`, `targetHumidity`, `setTargetHumidity` | AC, CC | Humidade interior e humidade definida (%) |
| `displayOn`, `toggleDisplay` | AC | Estado do ecrã e alternância |
| `purifier`, `purifierOn`, `purifierOff` / `purifierMode`, `setPurifierMode` | AC / CC | Purificador (AC: ligado/desligado; CC: `off`, `on`, `auto`) |
| `flash`, `outSilent`, `cascadeMode`, `freshAirFanSpeed`, `rateSelect`, `auxMode` + actions | AC (CC : `auxMode`) | Funções avançadas, consoante o modelo |
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Autolimpeza, alerta de filtro, descongelação, código de erro |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Potência (W) e consumos (kWh), se a opção *Consumo elétrico* estiver selecionada |
| `online`, `refresh` | AC, CC | Aparelho acessível (0/1) e atualização imediata |

## Resolução de problemas

| Mensagem | Solução |
|---|---|
| *Utilizador ou palavra-passe MSmartHome incorretos* | Verifique a conta na configuração do plugin. O plugin não volta a tentar enquanto as credenciais não mudarem. |
| *A nuvem da Midea bloqueou temporariamente a conta* | Demasiadas ligações (códigos `7610`, `65027`). Aguarde o tempo indicado sem iniciar outra sincronização. |
| *aparelho não emparelhado diretamente com esta conta (partilhado?)* | Na aplicação MSmartHome, emparelhe o aparelho com esta conta, e não apenas através de uma partilha. |
| *aparelho ausente da conta MSmartHome* | O aparelho está na rede mas noutra conta: introduza *token* e *key* manualmente, ou emparelhe-o com esta conta. |
| *chaves recusadas pelo aparelho* | Volte a usar **Obter token/key a partir da nuvem**; se o problema persistir, volte a emparelhar o aparelho na aplicação. |
| *aparelho não encontrado na rede local* / *inacessível* | Verifique se o aparelho está ligado e na mesma rede que o Jeedom, ou indique o **endereço de difusão** da sua rede. |

## Créditos

O plugin baseia-se nas bibliotecas de código aberto [msmart-ng](https://github.com/mill1000/midea-msmart) e [midea-local](https://github.com/midea-lan/midea-local).
