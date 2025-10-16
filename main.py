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
    # PRÉ
    "pre10": [
        "Aquecendo — entra pra pegar do começo às {hora}h! {link}",
        "Falta pouco pra {hora}h — posiciona e cola com a gente! {link}",
        "Reta final — não perde a abertura das {hora}h! {link}!",
        "Tua chance de começar certo hoje às {hora}h! {link}",
        "Contagem regressiva pra {hora}h — aproveita o fluxo! {link}!",
        "Vai começar às {hora}h — confirma presença! {link}",
        "Aquecendo pra {hora}h — resultado vem de quem aparece! {link}!",
        "Decisão agora: {hora}h é contigo! {link}!",
        "Preparação é tudo: {hora}h chegando — vem! {link}",
        "Sem enrolação, direto ao ponto às {hora}h! {link}",
        "As melhores janelas nascem no pré {hora}h — garante teu lugar! {link}!",
        "Últimos ajustes pra {hora}h — foco total! {link}",
        "O jogo vira às {hora}h — partiu! {link}!",
        "Constância > ansiedade: alinha pro {hora}h! {link}",
        "Quem chega antes, colhe melhor — {hora}h! {link}!",
        "Chama no compromisso: {hora}h é agora! {link}",
        "Acompanha o passo a passo no {hora}h! {link}!",
        "Reta final — {hora}h abrindo as portas! {link}",
        "Vem viver o ao vivo das {hora}h — execução simples! {link}!",
        "Presença manda — {hora}h é contigo! {link}!",
        "Não deixa pra depois: {hora}h é teu momento! {link}!",
        "Organiza e vem — {hora}h chegando! {link}",
        "Hoje você aparece pra você mesmo — {hora}h! {link}!",
        "O jogo começa no pré {hora}h — partiu! {link}!",
        "Alinha a mente pra {hora}h — vem! {link}",
        "Minuto final pra entrar no grupo — {hora}h! {link}!",
        "Tá pronto? {hora}h chegando — bora! {link}!",
        "Foco no simples no {hora}h — vem! {link}!",
        "Quem tá dentro chega agora — {hora}h! {link}!",
        "Presença = resultado — {hora}h! {link}!"
    ],
    "pre15": [
        "Hora de alinhar e vir junto às {hora}h! {link}",
        "{hora}h chegando — não deixa pra depois! {link}!",
        "Quem chega antes colhe melhor — {hora}h! {link}",
        "Aquecendo pra {hora}h — posiciona já! {link}!",
        "Vem pra {hora}h com a gente — simples e eficiente! {link}",
        "Prepara pra executar sem ansiedade às {hora}h! {link}!",
        "Reta final pra {hora}h — foco no playbook! {link}",
        "Tua meta passa por {hora}h — aparece! {link}!",
        "{hora}h é teu compromisso — confirma no grupo! {link}",
        "Passo a passo claro às {hora}h! {link}!",
        "Aquecimento {hora}h — presença conta! {link}",
        "Disciplina e execução no {hora}h — vem! {link}!",
        "Virar a chave às {hora}h — partiu! {link}",
        "Antes das {hora}h é a tua janela — entra! {link}!",
        "Posiciona e joga simples no {hora}h! {link}!",
        "Sem mistério: {hora}h é foco total! {link}",
        "Quem aparece, evolui — {hora}h! {link}!",
        "Últimos minutos pro {hora}h — cola no grupo! {link}",
        "Plano pronto pro {hora}h — só executar! {link}!",
        "Confirma {hora}h — presença valendo! {link}",
        "Primeiro passo às {hora}h — vem! {link}!",
        "Calma e clareza no {hora}h — cola! {link}",
        "Decide antes, domina no {hora}h — vem! {link}!",
        "Sem desculpa: {hora}h é ação! {link}!",
        "Não perde {hora}h — entra agora! {link}",
        "Prática com a equipe no {hora}h — vem! {link}",
        "Preparado? {hora}h chegando — presença! {link}",
        "Resultado acompanha quem tá no jogo — {hora}h! {link}!",
        "Atenção total pro {hora}h — confirma! {link}",
        "Hoje entrega — {hora}h! {link}!"
    ],
    "pre20": [
        "Última virada do dia — {hora}h pra fechar bonito! {link}",
        "{hora}h chegando: final de dia vira a chave! {link}!",
        "Aquecendo pra {hora}h — presença é meio caminho! {link}",
        "Nada de perder a última do dia — {hora}h! {link}!",
        "Reta final {hora}h — disciplina até o fim! {link}",
        "Quem vem pra {hora}h fecha o dia no controle! {link}!",
        "{hora}h quase aí — posiciona! {link}",
        "Reta final com decisão — {hora}h! {link}!",
        "Fecha o dia no alto: {hora}h! {link}",
        "Preparação simples, execução limpa — {hora}h! {link}!",
        "Virada de chave no {hora}h — sente o ritmo! {link}",
        "Chama na presença — {hora}h! {link}!",
        "Última do dia — {hora}h te coloca à frente! {link}",
        "Compromisso contigo — {hora}h! {link}!",
        "Respira, organiza e vem pro {hora}h! {link}",
        "Foco no necessário — {hora}h! {link}!",
        "Quem fecha no {hora}h colhe amanhã! {link}",
        "Decide agora pro {hora}h! {link}!",
        "Entrega total na {hora}h! {link}",
        "Sem desculpa: {hora}h é ação! {link}!",
        "Aquecimento final {hora}h — vem! {link}",
        "Presença manda — {hora}h! {link}!",
        "Últimos ajustes pra {hora}h — bora! {link}",
        "Bota o plano em prática — {hora}h! {link}!",
        "Sente o ritmo do {hora}h — abre o grupo! {link}",
        "Etapa decisiva do dia — {hora}h! {link}!",
        "Confirma {hora}h! {link}",
        "Teu movimento de hoje começa aqui — {hora}h! {link}!",
        "Quer fechar forte? vem no {hora}h! {link}",
        "Presença agora, resultado depois — {hora}h! {link}!"
    ],

    # PÓS
    "pos10": [
        "Sessão {hora}h tá pegando fogo — ainda dá tempo! {link}",
        "Já começou {hora}h e o ritmo tá forte — cola agora! {link}",
        "Depois das {hora}h o jogo virou — aproveita! {link}!",
        "{hora}h rolando: quem entrou já tá na frente — vem! {link}",
        "Fluxo bom no {hora}h — pega carona! {link}!",
        "Perdeu o começo? pós {hora}h ainda dá! {link}",
        "{hora}h ON: foco total e execução simples! {link}!",
        "Seguimos no pós {hora}h — consistência vence! {link}",
        "A galera já tá dentro {hora}h — confere! {link}!",
        "Sem desculpa, só ação no {hora}h! {link}!",
        "Janela aberta no {hora}h — aproveita! {link}",
        "Plano em execução no {hora}h — vem! {link}!",
        "Oportunidade real agora no {hora}h! {link}",
        "Ritmo bom no {hora}h — toma a frente! {link}!",
        "Ao vivo após {hora}h — sente o fluxo! {link}",
        "Quem tá dentro já avançou — vem pro {hora}h! {link}!",
        "Pós {hora}h: play direto! {link}",
        "Ainda dá tempo no {hora}h — chega mais! {link}!",
        "Aproveita a janela do {hora}h — chama no movimento! {link}",
        "Execução limpa no {hora}h — resultado aparece! {link}!",
        "Clima perfeito no {hora}h — entra agora! {link}",
        "Consistência e decisão no {hora}h — bora! {link}!",
        "Na prática após {hora}h — vamo! {link}",
        "Decidiu? participa — {hora}h ON! {link}!",
        "Oportunidade viva — {hora}h! {link}",
        "Ainda tá rolando {hora}h — aproveita! {link}!",
        "Presença que entrega no {hora}h! {link}!",
        "Vem ver com calma e clareza — {hora}h! {link}",
        "Joga simples no {hora}h — acompanha! {link}",
        "Execução pura — {hora}h! {link}!"
    ],
    "pos15": [
        "Movimento firme — entra no ritmo das {hora}h! {link}",
        "Sessão {hora}h rodando — bora pra prática! {link}!",
        "Plano rodando no {hora}h — vem! {link}",
        "Depois das {hora}h tem oportunidade pingando! {link}!",
        "Aproveita a janela, sem hesitar — {hora}h! {link}",
        "{hora}h ON — confirma presença e vem! {link}!",
        "Seguimos no {hora}h — consistência >>> ansiedade! {link}",
        "Ainda dá tempo nas {hora}h — chega mais! {link}!",
        "Chance real pra quem decide agora — {hora}h! {link}",
        "Ritmo bom — toma a frente no {hora}h! {link}!",
        "Fluxo continua — cola no {hora}h! {link}",
        "Clareza na execução — {hora}h! {link}!",
        "Quem tá dentro tá vendo — {hora}h! {link}",
        "Janela aberta nas {hora}h — aproveita! {link}!",
        "Decisão simples, play direto — {hora}h! {link}",
        "Ainda rolando {hora}h — chama no grupo! {link}!",
        "Presença que vira resultado — {hora}h! {link}",
        "Bora na prática após {hora}h — vem! {link}!",
        "Não fica de fora — aparece no {hora}h! {link}!",
        "Entra e acompanha — {hora}h! {link}!",
        "Execução limpa — sem drama — {hora}h! {link}",
        "Acontecendo agora — {hora}h! {link}!",
        "Segue o plano — {hora}h! {link}!",
        "Ao vivo no {hora}h — confere! {link}",
        "Constância na veia — {hora}h! {link}!",
        "No ar {hora}h — passa no grupo! {link}",
        "Chegou tua hora — {hora}h! {link}!",
        "Energia do {hora}h em alta — vem! {link}!",
        "Quem aparece, avança — {hora}h! {link}!",
        "Ainda dá tempo! {hora}h tá rolando! {link}!"
    ],
    "pos20": [
        "Reta final — ainda dá pra aproveitar forte às {hora}h! {link}",
        "Sessão {hora}h rodando — confere ao vivo! {link}!",
        "Fechamento do dia com foco total — {hora}h! {link}",
        "Não deixa passar — {hora}h! {link}!",
        "Ritmo forte após {hora}h — cola agora! {link}",
        "Quem tá no {hora}h já sentiu o fluxo — vem! {link}!",
        "Sem drama — só play no {hora}h! {link}",
        "Ainda há janela após {hora}h — chega mais! {link}!",
        "{hora}h tá quente — entra e acompanha! {link}",
        "Fechamento com consciência — {hora}h! {link}!",
        "Virada acontece no {hora}h — vem! {link}",
        "Foco no essencial e executa — {hora}h! {link}!",
        "Tudo acontecendo agora — abre o grupo! {link}",
        "Disciplina até o fim — {hora}h! {link}!",
        "Ainda em tempo — decide e vem no {hora}h! {link}",
        "Presença que fecha o dia certo — {hora}h! {link}",
        "No ar {hora}h — aproveita o embalo! {link}",
        "Chama no movimento — {hora}h! {link}",
        "Quem tá dentro tá vendo — {hora}h! {link}!",
        "Ritmo forte, execução clara — {hora}h! {link}",
        "Últimas oportunidades — cola no {hora}h! {link}!",
        "Fecha o dia de forma inteligente — {hora}h! {link}",
        "Ainda rolando {hora}h — participa! {link}!",
        "Chega pra sentir no ao vivo — {hora}h! {link}",
        "Mais uma chance — {hora}h! {link}!",
        "Simples, direto — pra dentro no {hora}h! {link}",
        "Quem aparece agora ganha amanhã — {hora}h! {link}!",
        "A turma tá avançando — {hora}h! {link}!",
        "Tu decide, tu colhe — {hora}h! {link}!",
        "Hora de entrar no jogo — {hora}h! {link}!"
    ],

    # EXTRAS
    "extra1130": [
        "Extra 11:30 — entra e confere! {link}!",
        "Oportunidade boa surgindo às 11:30! {link}",
        "11:30 ON — aproveita a janela! {link}!",
        "Extra 11:30: simples, direto e prático! {link}",
        "Bora na 11:30 — não deixa passar! {link}!",
        "Empurrão do meio da manhã — 11:30! {link}",
        "Foco no essencial — 11:30! {link}!",
        "Passa no grupo agora — 11:30 rolando! {link}!",
        "11:30: gás na medida! {link}",
        "Extra 11:30 — aparece e executa! {link}!",
        "Janela 11:30 aberta — aproveita! {link}",
        "Vem sentir o ritmo — 11:30! {link}!",
        "Muita coisa acontece 11:30 — confere! {link}",
        "Presença que gera resultado — 11:30! {link}!",
        "Chama no play — 11:30! {link}",
        "Confere o que tá rolando — 11:30! {link}!",
        "Oportunidade boa — 11:30! {link}",
        "Sem ansiedade — passo a passo 11:30! {link}",
        "Execução limpa às 11:30! {link}!",
        "Pinga na 11:30 e vem! {link}!",
        "Momento certeiro — 11:30! {link}",
        "Janelinha esperta — 11:30! {link}!",
        "Chamando geral — 11:30! {link}!",
        "Ritmo bom — 11:30! {link}",
        "Dá tempo de entrar e acompanhar — 11:30! {link}!",
        "Hoje tem — 11:30! {link}!",
        "Ponto de virada — 11:30! {link}",
        "Janela de confirmação — 11:30! {link}!",
        "Bora acelerar — 11:30! {link}",
        "Simples, direto e ao vivo — 11:30! {link}!"
    ],
    "extra1630": [
        "Extra 16:30 — acelera a tarde! {link}!",
        "16:30 ON — passa no grupo! {link}",
        "Oportunidade clara — 16:30! {link}!",
        "Hora de ajustar as velas — 16:30! {link}",
        "Janela boa surgindo — 16:30! {link}!",
        "Sem enrolar — 16:30! {link}",
        "Execução simples e direta — 16:30! {link}!",
        "Presença = resultado — 16:30! {link}",
        "Chega junto — 16:30 ON! {link}!",
        "Aproveita — 16:30! {link}",
        "Chama no movimento — 16:30! {link}!",
        "Virada da tarde — 16:30! {link}",
        "Ponto quente — 16:30! {link}!",
        "Foco e play — 16:30! {link}!",
        "Pega o timing — 16:30! {link}!",
        "Sem desculpa, só ação — 16:30! {link}",
        "Energia da tarde em alta — 16:30! {link}!",
        "Confirma presença e vem — 16:30! {link}",
        "Janela estratégica — 16:30! {link}!",
        "No ar 16:30 — chama no grupo! {link}",
        "Passo a passo claro — 16:30! {link}!",
        "Bora pro ao vivo — 16:30! {link}",
        "Decisão certa agora — 16:30! {link}!",
        "Janela 16:30 — aproveita! {link}",
        "Quem aparece, avança — 16:30! {link}!",
        "Play direto — 16:30! {link}",
        "Sente o fluxo — 16:30 ON! {link}!",
        "Dentro do jogo — 16:30! {link}",
        "Simples e efetivo — 16:30! {link}!",
        "Não perde essa — 16:30! {link}!"
    ],
    "extra1830": [
        "Extra 18:30 — aquece pra noite! {link}!",
        "18:30 ON — já prepara pra 20h! {link}",
        "Dá tempo de entrar — 18:30! {link}!",
        "Sente o fluxo — 18:30! {link}",
        "Sem ansiedade — passo a passo 18:30! {link}!",
        "Confirmando oportunidades — 18:30! {link}",
        "Janela boa — 18:30! {link}!",
        "Segue o plano — 18:30 ON! {link}",
        "Acelera o jogo — 18:30! {link}!",
        "Presença que conta — 18:30! {link}",
        "Ritmo certo pra noite — 18:30! {link}!",
        "Chama no grupo e vem — 18:30! {link}",
        "Pronto pro {hora}h — 18:30! {link}!",
        "Clareza e execução — 18:30! {link}!",
        "Play seguro e direto — 18:30! {link}",
        "Quem vem agora chega na frente — 18:30! {link}!",
        "Foco na prática — 18:30! {link}!",
        "Energia subindo — 18:30! {link}",
        "Bora aquecer — 18:30! {link}!",
        "Aparece e executa — 18:30 ON! {link}",
        "Timing perfeito — 18:30! {link}",
        "Vamo pra dentro — 18:30! {link}!",
        "Tá rolando — 18:30! {link}",
        "Vem pro ao vivo — 18:30! {link}!",
        "Responde presente — 18:30! {link}",
        "Ajuste final antes da noite — 18:30! {link}!",
        "Janela boa pra entrar — 18:30! {link}",
        "Intensidade certa — 18:30! {link}!",
        "Partiu grupo — 18:30! {link}",
        "Rumo às {hora}h — 18:30! {link}!"
    ],

    # BOA NOITE
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

# ================== EMOJIS (mix) ==================
EMOJIS_DEFAULT = ["🔥","💥","🚀","💰","⚡️","✅","📈","🎯","🟢"]
EMOJIS_BOANOITE = ["🌙","✨","😴","✅"]

def _has_trailing_emoji(s: str) -> bool:
    tail = "".join(EMOJIS_DEFAULT + EMOJIS_BOANOITE)
    return any(s.rstrip().endswith(e) for e in tail)

def add_emoji_variation(text: str, pool: str) -> str:
    if _has_trailing_emoji(text): return text
    if random.random() < 0.60:
        base = EMOJIS_BOANOITE if pool == "boanoite" else EMOJIS_DEFAULT
        one = random.choice(base)
        out = f"{text.rstrip()} {one}"
        if random.random() < 0.20:
            two = random.choice(base)
            if two != one: out = f"{out}{two}"
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

# ================== ROTINA / ENVIO ==================
def _next_index(context: ContextTypes.DEFAULT_TYPE, chat_id: int, pool: str) -> int:
    state = context.application.user_data.setdefault(chat_id, {})
    rot = state.setdefault("rot", {})
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

# ================== PDF ==================
async def send_bonus_pdf(context, chat_id):
    global FILE_ID
    caption = "📄 Guia Oráculo Black — o seu bônus de início!"
    try:
        if FILE_ID:
            await context.bot.send_document(chat_id, FILE_ID, caption=caption); return

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
                msg = await context.bot.send_document(chat_id, InputFile(f, filename=pdf_path.name), caption=caption)

        fid = msg.document.file_id if msg and msg.document else ""
        if fid:
            FILE_ID = fid
            log.info(f"[PDF] file_id capturado: {FILE_ID}")
            if ADMIN_ID:
                try: await context.bot.send_message(int(ADMIN_ID), f"PDF file_id:\n`{FILE_ID}`", parse_mode="Markdown")
                except Exception: pass
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
    # horários (BRT)
    _job(jq, f"pre_10_{chat_id}",   time(9,30,tzinfo=TZ),  chat_id, pre10_cb)
    _job(jq, f"pos_10_{chat_id}",   time(10,15,tzinfo=TZ), chat_id, pos10_cb)
    _job(jq, f"extra_1130_{chat_id}", time(11,30,tzinfo=TZ), chat_id, extra1130_cb)
    _job(jq, f"pre_15_{chat_id}",   time(14,30,tzinfo=TZ), chat_id, pre15_cb)
    _job(jq, f"pos_15_{chat_id}",   time(15,15,tzinfo=TZ), chat_id, pos15_cb)
    _job(jq, f"extra_1630_{chat_id}", time(16,30,tzinfo=TZ), chat_id, extra1630_cb)
    _job(jq, f"extra_1830_{chat_id}", time(18,30,tzinfo=TZ), chat_id, extra1830_cb)
    _job(jq, f"pre_20_{chat_id}",   time(19,30,tzinfo=TZ), chat_id, pre20_cb)
    _job(jq, f"pos_20_{chat_id}",   time(20,15,tzinfo=TZ), chat_id, pos20_cb)
    _job(jq, f"boanoite_{chat_id}", time(22, 0,tzinfo=TZ), chat_id, boanoite_cb)

async def restore_all_jobs(app):
    total = 0
    for chat_id, udata in app.user_data.items():
        if udata.get("onboarded"):
            await schedule_all_user_jobs(app.job_queue, chat_id); total += 1
    log.info(f"Restore: agendamentos reativados para {total} usuário(s).")

# Callbacks
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

# ---- Sessões (somente horários + semanal) ----
SEMANA = [
    ("Segunda-feira",  ["10:00", "15:00", "20:00"]),
    ("Terça-feira",    ["10:00", "15:00", "20:00"]),
    ("Quarta-feira",   ["10:00", "15:00", "20:00"]),
    ("Quinta-feira",   ["10:00", "15:00", "20:00"]),
    ("Sexta-feira",    ["10:00", "15:00", "20:00"]),
    ("Sábado",         ["10:00", "15:00", "20:00"]),
    ("Domingo",        ["10:00", "15:00", "20:00"]),
]

def _texto_sessoes():
    linhas = ["⚡ Sessões do dia", "• 10:00", "• 15:00", "• 20:00"]
    semana = ["", "📅 Cronograma semanal:"]
    for dia, hs in SEMANA:
        semana.append(f"• {dia}: " + ", ".join(hs))
    return "\n".join(linhas + semana)

async def cb_sessoes(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.callback_query.answer()
    await u.callback_query.message.reply_text(_texto_sessoes())

# -------- testes
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

# pools individuais
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

# pdf helpers
async def cmd_pdf(u,c):   await send_bonus_pdf(c, u.effective_chat.id); await u.message.reply_text("🧪 Tentativa de envio do PDF feita.")
async def cmd_where(u,c):
    pdf_path = (BASE_DIR / PDF_URL).resolve()
    await u.message.reply_text(f"🔎 PDF_URL={PDF_URL}\nBASE_DIR={BASE_DIR}\nRESOLVIDO={pdf_path}\nEXISTS={pdf_path.exists()}")

# help / unknown
async def cmd_help(u, c):
    txt = (
        "Comandos:\n"
        "/start /stop /help /sessoes\n"
        "/teste /agora /pdf /where\n"
        "/poolpre10 /poolpos10 /poolpre15 /poolpos15 /poolpre20 /poolpos20\n"
        "/poolextra1130 /poolextra1630 /poolextra1830 /poolboanoite"
    )
    await u.message.reply_text(txt)

async def cmd_unknown(u, c):
    name = (u.message.text or "").strip()
    logging.warning(f"[UNKNOWN CMD] {name} de {u.effective_chat.id}")
    await u.message.reply_text("⚠️ Comando não reconhecido. Use /help pra ver a lista.")

# ================== MAIN ==================
def main():
    persistence = PicklePersistence(filepath="state_oraculo_bot.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    async def _post_init(a): await restore_all_jobs(a)
    app.post_init = _post_init

    # 1) comandos
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("sessoes", lambda u,c: c.application.create_task(cb_sessoes(u,c))))
    app.add_handler(CommandHandler("teste",  cmd_teste))
    app.add_handler(CommandHandler("agora",  cmd_agora))
    app.add_handler(CommandHandler("pdf",    cmd_pdf))
    app.add_handler(CommandHandler("where",  cmd_where))

    # 2) pools
    app.add_handler(CommandHandler("poolpre10",     cmd_pool_pre10))
    app.add_handler(CommandHandler("poolpos10",     cmd_pool_pos10))
    app.add_handler(CommandHandler("poolpre15",     cmd_pool_pre15))
    app.add_handler(CommandHandler("poolpos15",     cmd_pool_pos15))
    app.add_handler(CommandHandler("poolpre20",     cmd_pool_pre20))
    app.add_handler(CommandHandler("poolpos20",     cmd_pool_pos20))
    app.add_handler(CommandHandler("poolextra1130", cmd_pool_extra1130))
    app.add_handler(CommandHandler("poolextra1630", cmd_pool_extra1630))
    app.add_handler(CommandHandler("poolextra1830", cmd_pool_extra1830))
    app.add_handler(CommandHandler("poolboanoite",  cmd_pool_boanoite))

    # 3) callback botão
    app.add_handler(CallbackQueryHandler(cb_sessoes, pattern="^sessoes$"))

    # 4) catch-all de comandos
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    # 5) texto comum
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Bot iniciado. Aguardando mensagens…")
    app.run_polling()

if __name__ == "__main__":
    main()
