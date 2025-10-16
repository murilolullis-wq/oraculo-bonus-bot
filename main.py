import os, logging, random
from pathlib import Path
from datetime import time, datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, PicklePersistence
)

# ================== LOG & TIMEZONE ==================
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("oraculo-bonus-bot")
TZ = ZoneInfo("America/Sao_Paulo")
BASE_DIR = Path(__file__).resolve().parent

# ================== ENV ==================
BOT_TOKEN  = os.getenv("BOT_TOKEN")
PDF_URL    = os.getenv("PDF_URL", "guia_oraculo_black.pdf").strip()
LINK_CAD   = os.getenv("LINK_CAD", "https://bit.ly/COMECENOORACULOBLACK").strip()
LINK_VIDEO = os.getenv("LINK_VIDEO", "https://t.me/oraculo_black_central/5").strip()
GRUPO_URL  = os.getenv("GRUPO_URL", "https://t.me/oraculoblackfree").strip()
FILE_ID    = os.getenv("FILE_ID", "").strip()
ADMIN_ID   = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente (.env/variables).")

# ================== MENSAGENS (30 por pool) ==================
POOLS = {
    "pre10": [
        "Pré {hora}h: aquecendo — entra pra pegar do começo! {link}!",
        "Falta pouco pra {hora}h — posiciona e cola com a gente! {link}",
        "Reta final antes das {hora}h — não perde a entrada boa! {link}!",
        "Pré {hora}h: tua chance de começar certo hoje! {link}",
        "Contagem regressiva pra {hora}h — aproveita o fluxo! {link}!",
        "Vai começar às {hora}h — confirma presença no grupo! {link}",
        "Aquecendo pra {hora}h — resultado vem de quem aparece! {link}!",
        "Pré {hora}h: decisão agora. Tá dentro? {link}!",
        "Preparação é tudo: {hora}h chegando — vem! {link}",
        "Ao vivo {hora}h: sem enrolação, direto ao ponto! {link}",
        "As melhores janelas nascem no pré {hora}h — garante teu lugar! {link}!",
        "Últimos ajustes pro {hora}h — foco total! {link}",
        "Se prepara: {hora}h é onde a turma vira o jogo! {link}!",
        "Pré {hora}h: constância > ansiedade. Vem simples e direto! {link}",
        "Quem chega antes, colhe melhor — {hora}h! {link}!",
        "Chama no compromisso: {hora}h é agora! {link}",
        "Pré {hora}h: entra e acompanha o passo a passo! {link}!",
        "Reta final — {hora}h vai abrir as portas! {link}",
        "Vem viver o ao vivo das {hora}h — execução simples! {link}!",
        "Pré {hora}h: presença manda! {link}!",
        "Não deixa pra depois: {hora}h é teu momento! {link}!",
        "Aquecimento {hora}h: organiza e vem! {link}",
        "Pré {hora}h: hoje você aparece pra você mesmo! {link}!",
        "O jogo começa no pré {hora}h — partiu! {link}!",
        "Hora de alinhar mentalidade pro {hora}h — vem! {link}",
        "Pré {hora}h: minuto final pra entrar no grupo! {link}!",
        "Tá pronto? {hora}h chegando — bora! {link}!",
        "Pré {hora}h: foco no simples e no claro! {link}!",
        "Quem tá dentro chega agora — {hora}h! {link}!",
        "Pré {hora}h: presença = resultado! {link}!"
    ],
    "pos10": [
        "Pós {hora}h: a sessão tá pegando fogo — ainda dá tempo de entrar! {link}!",
        "Já começou {hora}h e o ritmo tá forte — cola agora! {link}",
        "Depois das {hora}h o jogo virou — aproveita o momento! {link}!",
        "{hora}h rolando: quem entrou já tá na frente — chega junto! {link}",
        "A sessão {hora}h tá fluindo — pega carona no movimento! {link}!",
        "Perdeu o começo? Ainda dá tempo no pós {hora}h! {link}",
        "{hora}h ao vivo: foco total e execução simples! {link}!",
        "Seguimos no pós {hora}h — consistência vence! {link}",
        "A galera já tá dentro {hora}h — vem ver com os próprios olhos! {link}!",
        "Pós {hora}h: sem desculpa, só ação! {link}!",
        "Janela aberta no pós {hora}h — aproveita! {link}",
        "Quem entrou no {hora}h sabe: é executar o plano! {link}!",
        "Pós {hora}h: oportunidade real pra quem decide agora! {link}",
        "Ritmo bom no {hora}h — toma a frente! {link}!",
        "Ao vivo após {hora}h — vem sentir o fluxo! {link}",
        "Quem tá dentro já avançou — vem pro pós {hora}h! {link}!",
        "Pós {hora}h: sem drama, só play! {link}",
        "Ainda dá tempo no pós {hora}h — chega mais! {link}!",
        "Aproveita a janela do {hora}h — chama no movimento! {link}",
        "Pós {hora}h: execução limpa, resultado aparece! {link}!",
        "Clima perfeito no {hora}h — entra agora! {link}",
        "Pós {hora}h: consistência e decisão — bora! {link}!",
        "Na prática após {hora}h — sem teoria, vamo! {link}",
        "Quem decide agora, participa — pós {hora}h ON! {link}!",
        "Oportunidade viva no {hora}h — cola! {link}",
        "Ainda tá rolando {hora}h — aproveita o embalo! {link}!",
        "Pós {hora}h: presença que entrega! {link}!",
        "Vem ver com calma e clareza no pós {hora}h! {link}",
        "Joga simples: entra no {hora}h e acompanha! {link}",
        "Pós {hora}h: aqui é execução — partiu! {link}!"
    ],
    "pre15": [
        "Pré {hora}h: hora de alinhar e vir junto com a equipe! {link}",
        "{hora}h chegando — não deixa pra depois! {link}!",
        "Quem chega antes, colhe melhor — pré {hora}h! {link}",
        "Aquecendo pra {hora}h — entra e se posiciona! {link}!",
        "Vem pra {hora}h com a gente — simples e eficiente! {link}",
        "Pré {hora}h: prepara pra executar sem ansiedade! {link}!",
        "Reta final pra {hora}h — foco no playbook! {link}",
        "Tua meta do dia passa por {hora}h — aparece! {link}!",
        "{hora}h é teu compromisso de hoje — confirma no grupo! {link}",
        "Pré {hora}h: vamo de passo a passo claro! {link}!",
        "Aquecimento {hora}h — presença conta! {link}",
        "Pré {hora}h: disciplina e execução — vem! {link}!",
        "Momento de virar a chave às {hora}h — partiu! {link}",
        "Antes das {hora}h é a tua janela de ouro — entra! {link}!",
        "Pré {hora}h: posiciona e joga simples! {link}!",
        "Sem mistério: {hora}h é foco total! {link}",
        "Pré {hora}h: quem aparece, evolui — vem! {link}!",
        "Últimos minutos pro {hora}h — cola no grupo! {link}",
        "Pré {hora}h: o plano tá pronto — só executar! {link}!",
        "Chama pro {hora}h e garante presença! {link}",
        "Pré {hora}h: bora dar o primeiro passo! {link}!",
        "Aquecendo com calma e clareza {hora}h — vem! {link}",
        "Quem decide antes, domina no {hora}h — cola! {link}!",
        "Pré {hora}h: sem desculpa, só ação! {link}!",
        "Reta final {hora}h — entra pra não perder! {link}",
        "Pré {hora}h: bora pra prática com a equipe! {link}!",
        "Preparado? {hora}h chegando — presença! {link}",
        "Pré {hora}h: resultado acompanha quem tá no jogo! {link}!",
        "Atenção total pro {hora}h — confirma presença! {link}",
        "Pré {hora}h: vem que hoje entrega! {link}!"
    ],
    "pos15": [
        "Pós {hora}h: movimento firme — entra no ritmo certo! {link}",
        "A sessão {hora}h já tá rodando — bora pra prática! {link}!",
        "Quem entrou no {hora}h sabe: é executar o plano! {link}",
        "Depois das {hora}h: tem oportunidade pingando! {link}!",
        "Pós {hora}h: aproveita a janela, sem hesitar! {link}",
        "{hora}h tá ON — confirma presença e vem! {link}!",
        "Seguimos no {hora}h — consistência >>> ansiedade! {link}",
        "Ainda dá tempo no pós {hora}h — chega mais! {link}!",
        "Pós {hora}h: chance real pra quem decide agora! {link}",
        "Ritmo bom no {hora}h — toma a frente! {link}!",
        "Depois do {hora}h o fluxo continua — cola! {link}",
        "Pós {hora}h: clareza na execução — vem! {link}!",
        "Quem tá dentro tá vendo — entra no {hora}h! {link}",
        "Janela aberta no pós {hora}h — aproveita! {link}!",
        "Pós {hora}h: decisão simples, play direto! {link}",
        "Ainda rolando {hora}h — chama no grupo! {link}!",
        "Pós {hora}h: presença que vira resultado! {link}",
        "Na prática após {hora}h — bora! {link}!",
        "Pós {hora}h: não fica de fora — aparece! {link}!",
        "Fluxo bom no {hora}h — entra e acompanha! {link}!",
        "Pós {hora}h: execução limpa, sem drama! {link}",
        "Acontecendo agora no {hora}h — vem! {link}!",
        "Pós {hora}h: bora seguir o plano! {link}!",
        "Tudo ao vivo no {hora}h — confere! {link}",
        "Pós {hora}h: constância na veia! {link}!",
        "{hora}h no ar — passa no grupo! {link}",
        "Pós {hora}h: chegou a tua hora — entra! {link}!",
        "Aproveita a energia do {hora}h e vem! {link}!",
        "Pós {hora}h: quem aparece, avança! {link}!",
        "Ainda dá tempo! Pós {hora}h tá rolando! {link}!"
    ],
    "pre20": [
        "Pré {hora}h: última virada do dia — cola pra fechar bonito! {link}",
        "{hora}h chegando: final de dia é onde muita gente vira a chave! {link}!",
        "Aquecendo pra {hora}h — presença é meio caminho! {link}",
        "Pré {hora}h: nada de perder a última do dia! {link}!",
        "Reta final do dia {hora}h — disciplina até o fim! {link}",
        "Quem vem pra {hora}h fecha o dia no controle! {link}!",
        "{hora}h quase aí — confirma no grupo e se posiciona! {link}",
        "Pré {hora}h: reta final com decisão! {link}!",
        "Fecha o dia no alto: vem pra {hora}h! {link}",
        "Pré {hora}h: preparação simples, execução limpa! {link}!",
        "Virada de chave no {hora}h — cola pra sentir! {link}",
        "Pré {hora}h: chama na presença e aparece! {link}!",
        "Última do dia — {hora}h vai te colocar à frente! {link}",
        "Pré {hora}h: compromisso contigo mesmo — bora! {link}!",
        "Respira, organiza e vem pro {hora}h! {link}",
        "Pré {hora}h: foco no necessário — sem distração! {link}!",
        "Quem fecha o dia no {hora}h colhe mais amanhã! {link}",
        "Pré {hora}h: entra agora, decide agora! {link}!",
        "Reta final: {hora}h — entrega total! {link}",
        "Pré {hora}h: sem desculpa, só ação! {link}!",
        "Aquecimento final {hora}h — vem junto! {link}",
        "Pré {hora}h: presença manda — partiu! {link}!",
        "Últimos ajustes pro {hora}h — bora! {link}",
        "Pré {hora}h: bota o plano em prática! {link}!",
        "Vem sentir o ritmo do {hora}h — abre o grupo! {link}",
        "Pré {hora}h: etapa decisiva do dia — entra! {link}!",
        "Chama no grupo e confirma {hora}h! {link}",
        "Pré {hora}h: teu movimento de hoje começa aqui! {link}!",
        "Quem quer fechar o dia forte vem no {hora}h! {link}",
        "Pré {hora}h: presença agora, resultado depois! {link}!"
    ],
    "pos20": [
        "Pós {hora}h: reta final — ainda dá pra aproveitar forte! {link}",
        "Sessão {hora}h rodando — vem ver ao vivo! {link}!",
        "Depois das {hora}h é foco total até o fechamento! {link}",
        "Pós {hora}h: não deixa a oportunidade passar! {link}!",
        "Ritmo forte após {hora}h — cola agora! {link}",
        "Quem tá no {hora}h já sentiu o fluxo — vem junto! {link}!",
        "Pós {hora}h: execução sem drama, só play! {link}",
        "Ainda há janela após {hora}h — chega mais! {link}!",
        "{hora}h tá quente — entra e acompanha! {link}",
        "Pós {hora}h: fechamento com consciência! {link}!",
        "A virada acontece no pós {hora}h — vem! {link}",
        "Pós {hora}h: foca no essencial e executa! {link}!",
        "Tudo acontecendo agora no {hora}h — abre o grupo! {link}",
        "Pós {hora}h: disciplina até o fim! {link}!",
        "Ainda em tempo no {hora}h — decide e vem! {link}",
        "Pós {hora}h: presença que fecha o dia certo! {link}!",
        "No ar {hora}h — aproveita o embalo! {link}",
        "Pós {hora}h: chama no movimento! {link}",
        "Quem tá dentro tá vendo — entra no {hora}h! {link}!",
        "Pós {hora}h: ritmo forte, execução clara! {link}",
        "Últimas oportunidades no {hora}h — cola! {link}!",
        "Pós {hora}h: fecha o dia de forma inteligente! {link}",
        "Ainda rolando {hora}h — participa! {link}!",
        "Pós {hora}h: chega pra sentir no ao vivo! {link}",
        "Mais uma chance no {hora}h — bora! {link}!",
        "Pós {hora}h: simples, direto, pra dentro! {link}",
        "Quem aparece agora ganha amanhã — pós {hora}h! {link}!",
        "No {hora}h a turma tá avançando — vem! {link}!",
        "Pós {hora}h: tu decide, tu colhe! {link}!",
        "Hora de entrar no jogo — pós {hora}h! {link}!"
    ],
    "extra1130": [
        "Extra 11:30 — entra e confere! {link}!",
        "Ping 11:30: oportunidade boa surgindo! {link}",
        "11:30 ON — aproveita essa janela! {link}!",
        "Extra 11:30: simples, direto e prático! {link}",
        "Bora na 11:30 — não deixa passar! {link}!",
        "11:30 é o empurrão do meio da manhã — cola! {link}",
        "Extra 11:30: foco no essencial! {link}!",
        "Passa no grupo agora — 11:30 rolando! {link}!",
        "11:30: vamo dar o gás certo! {link}",
        "Extra 11:30 — aparece e executa! {link}!",
        "Janela 11:30 aberta — aproveita! {link}",
        "Extra 11:30: vem sentir o ritmo! {link}!",
        "No meio da manhã é onde muita coisa acontece — 11:30! {link}",
        "11:30 — presença que gera resultado! {link}!",
        "Extra 11:30: chama no play! {link}",
        "Confere o que tá rolando 11:30 — bora! {link}!",
        "Oportunidade boa 11:30 — chega mais! {link}",
        "Extra 11:30: sem ansiedade, só passo a passo! {link}",
        "11:30 ON — execução limpa! {link}!",
        "Pinga na 11:30 e vem pro grupo! {link}!",
        "Extra 11:30: momento certeiro! {link}",
        "Aproveita a 11:30 — janelinha esperta! {link}!",
        "11:30 chamando — vem junto! {link}!",
        "Extra 11:30 — ritmo bom, presença conta! {link}",
        "11:30: dá tempo de entrar e acompanhar! {link}!",
        "Extra 11:30: hoje tem! {link}!",
        "Ponto de virada na 11:30 — aparece! {link}",
        "Janela de confirmação 11:30 — cola! {link}!",
        "Extra 11:30: bora acelerar! {link}",
        "11:30 — simples, direto e ao vivo! {link}!"
    ],
    "extra1630": [
        "Extra 16:30 — acelera a tarde! {link}!",
        "16:30 ON — passa no grupo! {link}",
        "Ping 16:30: oportunidade clara! {link}!",
        "16:30: hora de ajustar as velas! {link}",
        "Extra 16:30 — janela boa surgindo! {link}!",
        "Vem na 16:30 — sem enrolar! {link}",
        "16:30: execução simples e direta! {link}!",
        "Extra 16:30 — presença = resultado! {link}",
        "16:30 ON — chega junto! {link}!",
        "16:30: bora aproveitar! {link}",
        "Extra 16:30: chama no movimento! {link}!",
        "16:30 é a virada da tarde — cola! {link}",
        "Ponto quente 16:30 — aparece! {link}!",
        "Extra 16:30: foco e play! {link}!",
        "16:30 ON — pega o timing! {link}!",
        "Extra 16:30: sem desculpa, só ação! {link}",
        "Energia da tarde em alta — 16:30! {link}!",
        "16:30: confirma presença e vem! {link}",
        "Extra 16:30: janela estratégica! {link}!",
        "16:30 no ar — chama no grupo! {link}",
        "Extra 16:30: passo a passo claro! {link}!",
        "16:30: bora pro ao vivo! {link}",
        "Extra 16:30 — decisão certa agora! {link}!",
        "Janela 16:30 — aproveita e cola! {link}",
        "16:30: quem aparece, avança! {link}!",
        "Extra 16:30: play direto! {link}",
        "16:30 ON — bora sentir o fluxo! {link}!",
        "Extra 16:30: tu dentro do jogo! {link}",
        "16:30: simples e efetivo! {link}!",
        "Extra 16:30 — não perde essa! {link}!"
    ],
    "extra1830": [
        "Extra 18:30 — aquece pra noite! {link}!",
        "18:30 ON — já prepara pra 20h! {link}",
        "Ping 18:30: dá tempo de entrar! {link}!",
        "18:30: vem sentir o fluxo! {link}",
        "Extra 18:30 — sem ansiedade, só passo a passo! {link}!",
        "18:30: confirmando oportunidades — cola! {link}",
        "Janela 18:30 — aparece agora! {link}!",
        "18:30 ON — segue o plano! {link}",
        "Extra 18:30 — acelera o jogo! {link}!",
        "18:30: presença que conta! {link}",
        "Extra 18:30: ritmo certo pra noite! {link}!",
        "18:30 — chama no grupo e vem! {link}",
        "Extra 18:30: tu pronto pro {hora}h! {link}!",
        "18:30 ON — clareza e execução! {link}!",
        "Extra 18:30: play seguro e direto! {link}",
        "18:30: quem vem agora chega na frente! {link}!",
        "Extra 18:30: foco na prática! {link}!",
        "18:30 — energia subindo, cola! {link}",
        "Extra 18:30: bora aquecer! {link}!",
        "18:30 ON — aparece e executa! {link}!",
        "Extra 18:30: timing perfeito! {link}",
        "18:30: vamo pra dentro! {link}!",
        "Extra 18:30: chama que tá rolando! {link}",
        "18:30 — vem pro ao vivo! {link}!",
        "Extra 18:30: responde presente! {link}",
        "18:30: ajuste final antes da noite! {link}!",
        "Extra 18:30: janela boa pra entrar! {link}",
        "18:30 ON — intensidade certa! {link}!",
        "Extra 18:30: partiu grupo! {link}",
        "18:30: rumo ao {hora}h — cola! {link}!"
    ],
    "boanoite": [
        "Fechamos o dia — amanhã te espero às 10h. Boa noite!",
        "Dia concluído. Descansa e volta amanhã com foco!",
        "Boa noite! Amanhã repetimos com consistência!",
        "Encerramos por hoje. Amanhã 10h tem mais!",
        "Boa noite — constância é o que te coloca na frente!",
        "Fecha o dia e vem renovado amanhã!",
        "Rotina vence: boa noite e até amanhã!",
        "Trabalho feito. Amanhã a gente continua!",
        "Desliga agora pra render amanhã. Boa noite!",
        "Amanhã tem mais — estarei te esperando!",
        "Gratidão pelo dia. Amanhã seguimos fortes!",
        "Boa noite — disciplina também é descanso!",
        "Fecha o ciclo de hoje; amanhã tem outro. Boa noite!",
        "Orgulhe-se do passo dado. Até amanhã!",
        "Foco e calma. Amanhã mais um capítulo!",
        "Encerramos aqui. Amanhã você aparece de novo!",
        "Prioriza o sono — ele multiplica teus resultados!",
        "Respira, relaxa e recarrega. Boa noite!",
        "Amanhã é dia de execução simples — até!",
        "Ritmo certo: hoje fecha, amanhã reabre!",
        "Mais um dia pra conta. Descansa bem!",
        "Amanhã eu conto contigo às 10h, combinado?",
        "Quem descansa bem, executa melhor. Boa noite!",
        "Zera a mente, mantém o compromisso. Boa noite!",
        "Amanhã a gente volta pro jogo — te espero!",
        "Fecha como campeão: descanso consciente!",
        "Boa noite — constância diária vence!",
        "Energia em recuperação: até amanhã!",
        "Reinicia o sistema: amanhã tem mais!",
        "Orgulho de te ter no time. Boa noite!"
    ]
}

# ================== EMOJIS (mix automático) ==================
EMOJIS_DEFAULT = ["🔥","💥","🚀","💰","⚡️","✅","📈","🎯","🟢"]
EMOJIS_BOANOITE = ["🌙","✨","😴","✅"]

def _has_trailing_emoji(s: str) -> bool:
    tail = "".join(EMOJIS_DEFAULT + EMOJIS_BOANOITE)
    return any(s.rstrip().endswith(e) for e in tail)

def add_emoji_variation(text: str, pool: str) -> str:
    if _has_trailing_emoji(text):
        return text
    if random.random() < 0.60:  # 60% das mensagens ganham emoji
        base = EMOJIS_BOANOITE if pool == "boanoite" else EMOJIS_DEFAULT
        one = random.choice(base)
        out = f"{text.rstrip()} {one}"
        if random.random() < 0.20:  # 20% ganham 2º emoji
            two = random.choice(base)
            if two != one:
                out = f"{out}{two}"
        return out
    return text

# ================== BOTÕES ==================
def teclado_variante():
    v = random.random()
    if v < 0.33:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)]])
    elif v < 0.66:
        return InlineKeyboardMarkup([[InlineKeyboardButton("ABRIR ✅", url=GRUPO_URL)]])
    else:
        btns = [InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD),
                InlineKeyboardButton("ABRIR ✅", url=GRUPO_URL)]
        random.shuffle(btns)
        return InlineKeyboardMarkup([btns])

def botoes_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)],
        [InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)],
        [InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")],
        [InlineKeyboardButton("ABRIR ✅", url=GRUPO_URL)]
    ])

# ================== ROTINA (rotação por usuário) ==================
def _next_index(context: ContextTypes.DEFAULT_TYPE, chat_id: int, pool: str) -> int:
    state = context.application.user_data.setdefault(chat_id, {})
    rot = state.setdefault("rot", {})   # rot[pool] = idx
    idx = (rot.get(pool, -1) + 1) % max(1, len(POOLS.get(pool, [])))
    rot[pool] = idx
    return idx

async def send_from_pool(pool: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int, hora: str | None = None):
    msgs = POOLS.get(pool, [])
    if not msgs: return
    idx = _next_index(context, chat_id, pool)
    nome = context.application.user_data.get(chat_id, {}).get("nome", "")
    txt = msgs[idx].replace("{hora}", hora or "").replace("{link}", GRUPO_URL).replace("{nome}", nome or "")
    txt = add_emoji_variation(txt, pool)
    await context.bot.send_message(chat_id, txt, reply_markup=teclado_variante())

# ================== PDF (local/URL/file_id) ==================
async def send_bonus_pdf(context, chat_id):
    global FILE_ID
    caption = "📄 Guia Oráculo Black — o seu bônus de início!"
    try:
        if FILE_ID:
            await context.bot.send_document(chat_id, FILE_ID, caption=caption)
            return

        if PDF_URL.lower().startswith("http"):
            msg = await context.bot.send_document(chat_id, PDF_URL, caption=caption)
        else:
            pdf_path = (BASE_DIR / PDF_URL).resolve()
            log.info(f"[PDF] path={pdf_path} exists={pdf_path.exists()} cwd={Path.cwd()} base={BASE_DIR}")
            if not pdf_path.exists():
                alt = Path("/app") / PDF_URL
                log.info(f"[PDF] alt={alt} exists={alt.exists()}")
                pdf_path = alt if alt.exists() else pdf_path
            with pdf_path.open("rb") as f:
                msg = await context.bot.send_document(
                    chat_id, InputFile(f, filename=pdf_path.name), caption=caption
                )

        fid = msg.document.file_id if msg and msg.document else ""
        if fid:
            FILE_ID = fid
            log.info(f"[PDF] file_id capturado: {FILE_ID}")
            if ADMIN_ID:
                try:
                    await context.bot.send_message(int(ADMIN_ID), f"PDF file_id:\n`{FILE_ID}`", parse_mode="Markdown")
                except Exception:
                    pass
    except Exception as e:
        log.exception(f"[PDF] erro: {e}")
        await context.bot.send_message(chat_id, "⚠️ Não consegui enviar o PDF agora. Tenta /start de novo depois.")

# ================== JOBS (agendas) ==================
def _job(jq, name, at: time, chat_id, cb):
    for j in jq.get_jobs_by_name(name): j.schedule_removal()
    job = jq.run_daily(cb, at, chat_id=chat_id, name=name)
    try: log.info(f"Agendado {name} -> {job.next_t.astimezone(TZ)}")
    except: pass

async def schedule_all_user_jobs(job_queue_or_context, chat_id: int):
    jq = getattr(job_queue_or_context, "job_queue", None) or job_queue_or_context
    _job(jq, f"pre_10_{chat_id}",   time(9,30,tzinfo=TZ),  chat_id, pre10_cb)
    _job(jq, f"pos_10_{chat_id}",   time(10,15,tzinfo=TZ), chat_id, pos10_cb)
    _job(jq, f"extra_1130_{chat_id}", time(11,30,tzinfo=TZ), chat_id, extra1130_cb)
    _job(jq, f"pre_15_{chat_id}",   time(14,30,tzinfo=TZ), chat_id, pre15_cb)
    _job(jq, f"pos_15_{chat_id}",   time(15,15,tzinfo=TZ), chat_id, pos15_cb)
    _job(jq, f"extra_1630_{chat_id}", time(16,30,tzinfo=TZ), chat_id, extra1630_cb)
    _job(jq, f"extra_1830_{chat_id}", time(18,30,tzinfo=TZ), chat_id, extra1830_cb)
    _job(jq, f"pre_20_{chat_id}",   time(19,30,tzinfo=TZ), chat_id, pre20_cb)
    _job(jq, f"pos_20_{chat_id}",   time(20,15,tzinfo=TZ), chat_id, pos20_cb)
    _job(jq, f"boanoite_{chat_id}", time(22,0,tzinfo=TZ),  chat_id, boanoite_cb)

async def restore_all_jobs(app):
    total = 0
    for chat_id, udata in app.user_data.items():
        if udata.get("onboarded"):
            await schedule_all_user_jobs(app.job_queue, chat_id); total += 1
    log.info(f"Restore: agendamentos reativados para {total} usuário(s).")

# Callbacks de jobs
async def pre10_cb(c):     await send_from_pool("pre10", c, c.job.chat_id, "10")
async def pos10_cb(c):     await send_from_pool("pos10", c, c.job.chat_id, "10")
async def pre15_cb(c):     await send_from_pool("pre15", c, c.job.chat_id, "15")
async def pos15_cb(c):     await send_from_pool("pos15", c, c.job.chat_id, "15")
async def pre20_cb(c):     await send_from_pool("pre20", c, c.job.chat_id, "20")
async def pos20_cb(c):     await send_from_pool("pos20", c, c.job.chat_id, "20")
async def extra1130_cb(c): await send_from_pool("extra1130", c, c.job.chat_id)
async def extra1630_cb(c): await send_from_pool("extra1630", c, c.job.chat_id)
async def extra1830_cb(c): await send_from_pool("extra1830", c, c.job.chat_id)
async def boanoite_cb(c):  await send_from_pool("boanoite", c, c.job.chat_id)

# ================== HANDLERS ==================
async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    if c.user_data.get("onboarded"):
        await u.message.reply_text("Menu rápido 👇", reply_markup=botoes_menu()); return
    await u.message.reply_text("Opa, seja bem-vindo 😎 Me fala seu nome e já libero teu bônus!")
    c.user_data["awaiting_name"] = True

async def cmd_stop(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    c.user_data.clear()
    for j in c.job_queue.jobs():
        if j.chat_id == chat_id: j.schedule_removal()
    await u.message.reply_text("Agendamentos limpos. Envie /start para recomeçar.")

async def on_text(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    if c.user_data.get("awaiting_name"):
        nome = (u.message.text or "").strip()
        c.user_data["nome"] = nome
        c.user_data["awaiting_name"] = False
        await u.message.reply_text(f"Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇")
        await send_bonus_pdf(c, chat_id)
        await u.message.reply_text("Atalhos rápidos pra começar 👇", reply_markup=botoes_menu())
        await schedule_all_user_jobs(c, chat_id)
        c.user_data["onboarded"] = True
        return
    await u.message.reply_text("Escolha uma opção 👇", reply_markup=botoes_menu())

async def cb_sessoes(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.callback_query.answer()
    txt = ("⚡ Sessões do dia\n"
           "• 09:30 — Pré 10h\n"
           "• 10:15 — Pós 10h\n"
           "• 11:30 — Extra\n"
           "• 14:30 — Pré 15h\n"
           "• 15:15 — Pós 15h\n"
           "• 16:30 — Extra\n"
           "• 18:30 — Extra\n"
           "• 19:30 — Pré 20h\n"
           "• 20:15 — Pós 20h\n"
           "• 22:00 — Boa noite")
    await u.callback_query.message.reply_text(txt)

# -------- testes rápidos
async def cmd_teste(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    await send_from_pool("pre10", c, chat_id, "10")
    await send_from_pool("pos10", c, chat_id, "10")
    await send_from_pool("extra1130", c, chat_id)
    await send_from_pool("boanoite", c, chat_id)
    await u.message.reply_text("✅ Testes enviados.")

async def cmd_agora(u: Update, c: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TZ).time(); chat_id = u.effective_chat.id
    if   now < time(10,0,tzinfo=TZ):  await send_from_pool("pre10", c, chat_id, "10")
    elif now < time(15,0,tzinfo=TZ):  await send_from_pool("pre15", c, chat_id, "15")
    elif now < time(20,0,tzinfo=TZ):  await send_from_pool("pre20", c, chat_id, "20")
    else:                              await send_from_pool("boanoite", c, chat_id)
    await u.message.reply_text("✅ Mensagem ‘agora’ enviada.")

# -------- comandos pool específicos (inclui /poolpos10)
async def cmd_pool_pre10(u,c):      await send_from_pool("pre10", c, u.effective_chat.id, "10")
async def cmd_pool_pos10(u,c):      await send_from_pool("pos10", c, u.effective_chat.id, "10")
async def cmd_pool_pre15(u,c):      await send_from_pool("pre15", c, u.effective_chat.id, "15")
async def cmd_pool_pos15(u,c):      await send_from_pool("pos15", c, u.effective_chat.id, "15")
async def cmd_pool_pre20(u,c):      await send_from_pool("pre20", c, u.effective_chat.id, "20")
async def cmd_pool_pos20(u,c):      await send_from_pool("pos20", c, u.effective_chat.id, "20")
async def cmd_pool_extra1130(u,c):  await send_from_pool("extra1130", c, u.effective_chat.id)
async def cmd_pool_extra1630(u,c):  await send_from_pool("extra1630", c, u.effective_chat.id)
async def cmd_pool_extra1830(u,c):  await send_from_pool("extra1830", c, u.effective_chat.id)
async def cmd_pool_boanoite(u,c):   await send_from_pool("boanoite", c, u.effective_chat.id)

# -------- PDF debug
async def cmd_pdf(u,c):   await send_bonus_pdf(c, u.effective_chat.id); await u.message.reply_text("🧪 Tentativa de envio do PDF feita.")
async def cmd_where(u,c):
    pdf_path = (BASE_DIR / PDF_URL).resolve()
    await u.message.reply_text(f"🔎 PDF_URL={PDF_URL}\nBASE_DIR={BASE_DIR}\nRESOLVIDO={pdf_path}\nEXISTS={pdf_path.exists()}")

# ================== MAIN ==================
def main():
    persistence = PicklePersistence(filepath="state_oraculo_bot.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    async def _post_init(a): await restore_all_jobs(a)
    app.post_init = _post_init

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop",  cmd_stop))
    app.add_handler(CommandHandler("teste", cmd_teste))
    app.add_handler(CommandHandler("agora", cmd_agora))
    app.add_handler(CallbackQueryHandler(cb_sessoes, pattern="^sessoes$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # pools individuais (inclui o que você digitou)
    app.add_handler(CommandHandler("poolpre10",  cmd_pool_pre10))
    app.add_handler(CommandHandler("poolpos10",  cmd_pool_pos10))   # << /poolpos10
    app.add_handler(CommandHandler("poolpre15",  cmd_pool_pre15))
    app.add_handler(CommandHandler("poolpos15",  cmd_pool_pos15))
    app.add_handler(CommandHandler("poolpre20",  cmd_pool_pre20))
    app.add_handler(CommandHandler("poolpos20",  cmd_pool_pos20))
    app.add_handler(CommandHandler("poolextra1130", cmd_pool_extra1130))
    app.add_handler(CommandHandler("poolextra1630", cmd_pool_extra1630))
    app.add_handler(CommandHandler("poolextra1830", cmd_pool_extra1830))
    app.add_handler(CommandHandler("poolboanoite", cmd_pool_boanoite))

    # pdf helpers
    app.add_handler(CommandHandler("pdf",   cmd_pdf))
    app.add_handler(CommandHandler("where", cmd_where))

    log.info("Bot iniciado. Aguardando mensagens…")
    app.run_polling()

if __name__ == "__main__":
    main()
