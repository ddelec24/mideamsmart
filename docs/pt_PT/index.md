# Plugin Midea MSmart

> **Plugin em desenvolvimento**: esta documentação descreve o estado atual do plugin e será completada a cada versão.

## Apresentação

O plugin **Midea MSmart** permite controlar **localmente** os aparelhos de ar condicionado e desumidificadores Midea e de marcas associadas (Comfee, Inventor, Qlima…) compatíveis com a aplicação **MSmartHome**.

A conta MSmartHome serve apenas para:

- listar os aparelhos associados à conta;
- obter uma única vez as chaves de autenticação (*token* e *key*) dos aparelhos recentes (protocolo V3).

Depois disso, todos os comandos e leituras de estado passam diretamente pela rede local, sem a nuvem da Midea.

O plugin inclui uma programação horária, com perfis comuns a todos os aparelhos (por exemplo *Normal* e *Férias*).

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
  - **Duração das ligações**: os aparelhos de ar condicionado são religados após este tempo (90 s por predefinição). Alguns aparelhos cortam eles próprios a ligação ao fim de algum tempo, o que provoca erros e quebras: um valor inferior a esse tempo evita-os. 0 = ligação mantida indefinidamente.
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
  - **Duração da ligação** (ar condicionado): deixe vazio para usar o valor da configuração do plugin.
  - **Bip de confirmação**: o aparelho emite um bip a cada comando recebido.
  - **Passo da temperatura definida** (ar condicionado): 1 °C ou 0,5 °C.
  - **Consumo elétrico** (ar condicionado): cria os comandos de potência e consumo. Se os valores forem incoerentes, altere o **formato** (BCD ou binário) ou o **fator de escala**.
- **Informações**
  - Número de série e modelo do aparelho, apenas de leitura.
  - **Capacidades**: *Recebidas do aparelho*, ou *Predefinidas* se o aparelho ainda não as enviou. Nesse caso são pedidas de novo automaticamente, e os comandos são ajustados assim que são recebidas.

> **Importante**
>
> Guarde o *token* e a *key* dos seus aparelhos V3 num local seguro. Permitem continuar a controlar os aparelhos mesmo que a nuvem da Midea fique indisponível.

## Comandos

![Widgets do ar condicionado e do desumidificador](../images/dashboard_ac.png) ![](../images/dashboard_a1.png)

![Separador Comandos](../images/device_commands.png)

Os comandos são criados automaticamente **de acordo com as capacidades comunicadas por cada aparelho**, assim que responde pela primeira vez. Se o aparelho não devolver as suas capacidades, são usadas capacidades predefinidas e o pedido é repetido após 30 segundos e depois em intervalos crescentes até 10 minutos. Quando são recebidas, os comandos são ajustados automaticamente.

Os comandos info de tipo texto contêm um **código estável**, independente do idioma (por exemplo `cool`): use estes códigos nos seus cenários. Os comandos action associados propõem etiquetas traduzidas. As infos já apresentadas por uma ação ligada ficam ocultas por predefinição.

O botão **Atualizar os comandos** do separador *Comandos* adiciona os comandos em falta, remove os das funções que o aparelho já não declara e volta a ler as suas capacidades. Os nomes e definições dos comandos existentes são mantidos. Os comandos que adicionou ao equipamento (identificador lógico desconhecido do plugin) nunca são removidos.

| Identificador lógico | Aparelhos | Conteúdo |
|---|---|---|
| `power`, `on`, `off` | AC, CC, A1 | Estado (0/1), ligar, desligar |
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
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Autolimpeza, alerta de filtro, descongelação (só se o aparelho a comunicar), código de erro |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Potência (W) e consumos (kWh), se a opção *Consumo elétrico* estiver selecionada |
| `mode`, `setMode` | A1 | Modo: `manual`, `continuous`, `auto`, `clothes_dry`, `shoes_dry`, `silent`. Escolher um modo liga o aparelho |
| `fanSpeed`, `setFanSpeed` | A1 | Ventilação: `lowest`, `low`, `medium`, `high`, `auto` |
| `currentHumidity`, `currentTemperature`, `targetHumidity`, `setTargetHumidity` | A1 | Humidade e temperatura ambiente, humidade definida de 35 a 85 % |
| `tankLevel`, `tankFull`, `waterLevelSet`, `setWaterLevelSet` | A1 | Nível do depósito (%), depósito cheio, limite do depósito (`25`, `50`, `75`, `100`) |
| `swing`, `childLock`, `anion`, `pump` + `…On`, `…Off` | A1 | Oscilação, bloqueio para crianças, ionizador, bomba (se o aparelho tiver uma) |
| `filterCleaningReminder`, `resetFilter` | A1 | Lembrete de limpeza do filtro e a sua reposição |
| `online`, `refresh` | AC, CC, A1 | Aparelho acessível (0/1) e atualização imediata |
| `scheduleEnabled`, `scheduleOn`, `scheduleOff` | AC, CC, A1 | Programação seguida (0/1), seguir e suspender a programação do aparelho |
| `profile`, `setProfile` | Programação | Nome do perfil ativo e escolha do perfil (identificador ou nome) |

## Programação

O plugin pode comandar os seus aparelhos segundo horários, por exemplo com um programa para o período escolar e outro para as férias. Tudo acontece no Jeedom, em local. Os programas da aplicação MSmartHome não são acessíveis a partir da rede local: desative-os para evitar conflitos.

### Perfis comuns

![Perfis de programação](../images/scheduler.png)

O mosaico **Programação** da página do plugin abre o equipamento *Programação*, criado automaticamente. Contém os **perfis**, comuns a todos os aparelhos (*Normal* e *Férias* por predefinição):

- adicione, mude o nome ou elimine perfis e depois guarde;
- escolha o **perfil ativo** aqui, ou com o comando de ação *Escolher o perfil* (`setProfile`), por exemplo num cenário lançado no início e no fim das férias. O comando também aceita o nome do perfil;
- o comando de informação *Perfil* (`profile`) dá o nome do perfil ativo;
- desativar o equipamento *Programação* suspende a programação de todos os aparelhos.

### Períodos de cada aparelho

![Separador Programação](../images/device_schedule.png)

O separador **Programação** de cada aparelho contém os seus períodos. Um período inclui:

- um perfil, dias e uma hora;
- uma ação: **Ligar** ou **Desligar**;
- para *Ligar*, definições opcionais: modo, temperatura definida, ventilação e predefinição (por exemplo *Noite*) para um ar condicionado; modo, humidade e ventilação para um desumidificador. Uma definição vazia não é alterada, e escolher um modo liga o aparelho.

Só se aplicam os períodos do perfil ativo. A lista **Mostrar** filtra a tabela por perfil, e um novo período é adicionado no perfil mostrado.

Opções do aparelho:

- **Seguir a programação**: o aparelho aplica os seus períodos. Os comandos *Seguir a programação* (`scheduleOn`) e *Suspender a programação* (`scheduleOff`) fazem o mesmo a partir de um cenário, e a informação *Programação seguida* (`scheduleEnabled`) dá o estado;
- **Recuperação** (ativada por predefinição): ao mudar de perfil, ao retomar a programação ou ao reiniciar o Jeedom, o último período passado é aplicado de imediato, sem esperar pelo seguinte. Por exemplo, ao passar para *Férias* às 10 h, o ar condicionado assume o estado previsto pelo período das 8 h do perfil *Férias*.

A saber:

- os períodos são verificados a cada minuto pela tarefa *cron* do plugin, que deve continuar ativa na configuração do plugin;
- uma definição manual (comando à distância, widget, cenário) mantém-se até ao período seguinte;
- adicionar ou alterar um período não aplica nada de imediato: o próximo período é aplicado à sua hora.

Exemplo para um ar condicionado, no período escolar e nas férias:

| Perfil | Dias | Hora | Ação |
|---|---|---|---|
| Normal | Seg a Sex | 07:00 | Ligar, Aquecimento, 21 °C |
| Normal | Seg a Sex | 08:00 | Ligar, 18 °C |
| Normal | Seg a Sex | 16:30 | Ligar, Aquecimento, 21 °C |
| Normal | Seg a Sex | 20:30 | Ligar, 19 °C, predefinição Noite |
| Férias | Seg a Dom | 08:00 | Ligar, Aquecimento, 20 °C |
| Férias | Seg a Dom | 21:00 | Desligar |

## Diagnóstico e fiabilidade

![Diagnóstico](../images/device_diagnostic.png)

- **Diagnóstico** (botão no topo da página do equipamento): mostra a configuração vista pelo Jeedom e o estado visto pelo daemon (ligação, última resposta, último erro, capacidades e valores brutos do aparelho). O botão **Copiar para o fórum** copia este resumo, sem palavra-passe, *token* nem *key*, pronto a colar num pedido de ajuda no [fórum Jeedom](https://community.jeedom.com).
- **Aparelho inacessível**: o comando `online` passa a 0 e o equipamento é assinalado em *timeout* no Jeedom. As consultas são progressivamente espaçadas, até uma a cada 5 minutos, e retomam o ritmo normal assim que o aparelho responde.
- **Mudança de endereço IP**: se um aparelho não responder há 5 minutos, o daemon procura-o na rede local (no máximo uma vez a cada 10 minutos, sem a nuvem). Se o encontrar noutro endereço, o endereço IP do equipamento é atualizado automaticamente. Ainda assim, recomenda-se reservar o endereço dos seus aparelhos no router.
- **Proteção da conta MSmartHome**: um bloqueio da nuvem (códigos `7610`, `65027`) ou uma palavra-passe recusada é memorizado, mesmo após um reinício do daemon. Durante um bloqueio, a sincronização limita-se à rede local e a obtenção das chaves é recusada. Uma palavra-passe recusada não volta a ser tentada até ser alterada.
- **Página Saúde** do Jeedom: indica o número de aparelhos acessíveis e o estado da conta MSmartHome.

## Resolução de problemas

| Mensagem | Solução |
|---|---|
| *Network error … Transport is closing or closed* (warning) | O aparelho cortou a ligação: o plugin volta a ligar-se e repete o pedido de imediato. Se esta mensagem for frequente, diminua a **duração das ligações** (por exemplo 60 s). |
| *Payload … failed CRC and checksum* (warning) | Trama inválida ignorada pela biblioteca, muitas vezes ligada a quebras de ligação: mesma solução que acima. |
| Comandos a mais, ou diferentes entre aparelhos idênticos | As capacidades não foram recebidas (indicador *Capacidades* do equipamento): são pedidas de novo automaticamente. Também pode clicar em **Atualizar os comandos**. |
| *Utilizador ou palavra-passe MSmartHome incorretos* | Verifique a conta na configuração do plugin. O plugin não volta a tentar enquanto as credenciais não mudarem. |
| *A nuvem da Midea bloqueou temporariamente a conta* | Demasiadas ligações (códigos `7610`, `65027`). Aguarde o tempo indicado sem iniciar outra sincronização. |
| *aparelho não emparelhado diretamente com esta conta (partilhado?)* | Na aplicação MSmartHome, emparelhe o aparelho com esta conta, e não apenas através de uma partilha. |
| *aparelho ausente da conta MSmartHome* | O aparelho está na rede mas noutra conta: introduza *token* e *key* manualmente, ou emparelhe-o com esta conta. |
| *chaves recusadas pelo aparelho* | Volte a usar **Obter token/key a partir da nuvem**; se o problema persistir, volte a emparelhar o aparelho na aplicação. |
| *aparelho não encontrado na rede local* / *inacessível* | Verifique se o aparelho está ligado e na mesma rede que o Jeedom, ou indique o **endereço de difusão** da sua rede. |

## Créditos

O plugin baseia-se nas bibliotecas de código aberto [msmart-ng](https://github.com/mill1000/midea-msmart) e [midea-local](https://github.com/midea-lan/midea-local).

O plugin é concebido e dirigido por **ddelec24** (maestro do projeto) e desenvolvido com **Claude** (Anthropic), coautor do código e da documentação.
