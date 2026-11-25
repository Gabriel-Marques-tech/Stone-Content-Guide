"""Canais selecionados à mão: público declaradamente MPE no título ou na descrição.

Critérios: conteúdo voltado a quem tem (ou abre) um pequeno negócio, diversidade de tamanho de
conta e de tema, e no máximo 8 canais do Sebrae para o sistema não dominar a base.
(handle, perfil, segmento)
"""

CANAIS = [
    # instituições
    ("@sebrae", "instituicao", "geral"),
    ("@sebraetalks", "instituicao", "geral"),
    ("@sebraespaulo", "instituicao", "geral"),
    ("@sebraeproficial", "instituicao", "geral"),
    ("@sebraesc", "instituicao", "geral"),
    ("@sebraeminas", "instituicao", "geral"),
    ("@sebraersoficial", "instituicao", "geral"),
    ("@sebraebahia", "instituicao", "geral"),
    # marcas e fintechs (handles prováveis: os inexistentes são descartados na coleta)
    ("@stone", "marca", "geral"),
    ("@infinitepay", "marca", "geral"),
    ("@contaazul", "marca", "geral"),
    ("@nuvemshop", "marca", "varejo"),
    ("@pagbank", "marca", "geral"),
    ("@sumupbrasil", "marca", "geral"),
    ("@programaconsumerbr", "marca", "alimentacao"),
    ("@sischef", "marca", "alimentacao"),
    ("@awisemais", "marca", "geral"),
    ("@agilizecontabilidadeonline", "marca", "geral"),
    # contabilidade e MEI
    ("@contabilidadefacilitada", "especialista", "geral"),
    ("@centraldomicroempreendedor", "especialista", "geral"),
    ("@accuredigital", "especialista", "geral"),
    ("@gustavoribeiromei", "especialista", "geral"),
    ("@descomplicandoosimples", "especialista", "geral"),
    ("@informeitributos", "especialista", "geral"),
    ("@transparenciacontabilidadeporl", "especialista", "geral"),
    ("@claccontabilidade", "especialista", "geral"),
    ("@lcontdesenvolvimentocontabil", "especialista", "geral"),
    ("@contadordevalor", "especialista", "geral"),
    ("@mateuscontador", "especialista", "geral"),
    ("@otiagojotta", "especialista", "geral"),
    ("@dicasparaomei", "empreendedor", "geral"),
    # gestão e finanças
    ("@allmanconsultoria", "especialista", "geral"),
    ("@paulomattosmentor", "especialista", "geral"),
    ("@cleberbrandao", "especialista", "geral"),
    ("@rodrigofinancas", "especialista", "geral"),
    ("@mnegocioproprio", "especialista", "geral"),
    ("@pamelacavalcanteadm", "especialista", "geral"),
    ("@empreendedoresemacao", "especialista", "geral"),
    ("@michellinezambon", "especialista", "geral"),
    ("@empreendacomadani", "especialista", "geral"),
    # maquininhas
    ("@maquinadecartaoboa", "especialista", "geral"),
    ("@clubedasmaquininhas", "especialista", "geral"),
    ("@mcbr", "especialista", "geral"),
    ("@sheilacuenca", "especialista", "geral"),
    # alimentação
    ("@paznodelivery-michel", "especialista", "alimentacao"),
    ("@marcelomarani", "especialista", "alimentacao"),
    ("@raphaelsilvadelivery", "especialista", "alimentacao"),
    ("@deliverysempreguicawdsonjunior", "especialista", "alimentacao"),
    ("@deliveryifood", "especialista", "alimentacao"),
    ("@eusounicolasmonteiro", "especialista", "alimentacao"),
    ("@felipecal.gestao", "especialista", "alimentacao"),
    ("@matheusbrayan1", "especialista", "alimentacao"),
    ("@gestaodepizzarias", "especialista", "alimentacao"),
    ("@hamburgueiroraiz", "especialista", "alimentacao"),
    # varejo
    ("@kkstoredesign", "especialista", "varejo"),
    ("@olojistadesucesso", "especialista", "varejo"),
    ("@meumercadinho", "empreendedor", "varejo"),
    ("@dicasdoandreluiz", "empreendedor", "varejo"),
    ("@multimarcaskarina", "empreendedor", "varejo"),
    ("@daniribeiro2704", "empreendedor", "varejo"),
    ("@julianepanaro", "empreendedor", "varejo"),
    ("@oadrianocavalcante", "empreendedor", "varejo"),
    ("@tendideias", "especialista", "varejo"),
    # beleza
    ("@upbarbearia", "especialista", "beleza"),
    ("@marcusturati", "especialista", "beleza"),
    ("@gilsonaugustinhaki-l4n", "especialista", "beleza"),
]
