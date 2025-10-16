import os, random, logging, asyncio
from datetime import datetime, date, time, timedelta
import pytz

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

# ================= LOG =================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("oraculo-bonus-bot")

# ============== ENV VARS ==============
BOT_TOKEN  = os.getenv("BOT_TOKEN")
LINK_CAD   = os.getenv("LINK_CAD")        # cadastro/depósito/HomeBroker
LINK_VIDEO = os.getenv("LINK_VIDEO", "")  # opcional
PDF_URL    = os.getenv("PDF_URL", "")     # PDF bônus
GROUP_LINK = os.getenv("GROUP_LINK", "")  # opcional

TZ = pytz.timezone("America/Sao_Paulo")

# ============== STATE ==============
ASK_NAME = 1
SUBSCRIBERS: set[int] = set()
USERS: dict[int, str] = {}  # chat_id -> nome

# controle de repetição diária (por horário/ocasião)
USED_TODAY: dict[str, set[str]] = {
    "pre_m": set(), "pre_t": set(), "pre_n": set(),
    "during_m": set(), "during_t": set(), "during_n": set(),
    "post_m": set(), "post_t": set(), "post_n": set(),
    "goodnight": set()
}
LAST_BUILD_DAY: date = date.min

# ============== HELPERS ==============
EMOJIS = ["💰","🔥","📈","⚡","🚀","📊","💎","😎","💥","🏆"]

def today_br() -> date:
    return datetime.now(TZ).date()

def maybe_emoji(text: str) -> str:
    return f"{text} {random.choice(EMOJIS)}" if random.random() < 0.6 else text

def name_of(chat_id: int) -> str:
    return USERS.get(chat_id, "").strip()

def personalize(raw: str, chat_id: int) -> str:
    nome = name_of(chat_id)
    if "{nome}" in raw:
        return raw.replace("{nome}", nome or "você")
    if nome and raw and random.random() < 0.35:
        return f"{nome}, {raw[0].lower() + raw[1:]}"
    return raw

def cta_keyboard() -> InlineKeyboardMarkup:
    rows = []
    # Alterna a ordem dos CTAs
    if random.random() < 0.5:
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
        if GROUP_LINK:
            rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    else:
        if GROUP_LINK:
            rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
    # Vídeo às vezes
    if LINK_VIDEO and random.random() < 0.4:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    return InlineKeyboardMarkup(rows)

def fixed_shortcuts_keyboard() -> InlineKeyboardMarkup:
    btns = []
    if LINK_VIDEO:
        btns.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    btns.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
    btns.append([InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")])
    if GROUP_LINK:
        btns.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    return InlineKeyboardMarkup(btns)

def br_time(h: int, m: int = 0) -> time:
    return time(h, m, tzinfo=TZ)

def jitter(t: time, minus=5, plus=5) -> time:
    # cria um datetime "hoje" no fuso BR a partir do time e aplica jitter
    now = datetime.now(TZ)
    base = TZ.localize(datetime(now.year, now.month, now.day, t.hour, t.minute))
    dmin = random.randint(-minus, plus)
    return (base + timedelta(minutes=dmin)).timetz()

# ============== GERADOR DE 90 MENSAGENS POR OCASIÃO ==============
def build_pool(prefixes, cores, closes, target=90):
    combos = []
    for p in prefixes:
        for c in cores:
            for cl in closes:
                combos.append(f"{p} {c}{cl}")
                if len(combos) >= target * 3:  # gera bastante, depois filtra
                    break
            if len(combos) >= target * 3:
                break
        if len(combos) >= target * 3:
            break
    random.shuffle(combos)
    seen, final = set(), []
    for s in combos:
        if s not in seen:
            final.append(s)
            seen.add(s)
        if len(final) >= target:
            break
    return final

def split_3x30(pool: list[str]):
    """Recebe 90 e devolve 3 listas de 30: (manhã, tarde, noite)."""
    if len(pool) < 90:
        ext = pool.copy()
        random.shuffle(ext)
        while len(pool) < 90 and ext:
            pool.append(random.choice(ext))
    m = pool[0:30]
    t = pool[30:60]
    n = pool[60:90]
    return m, t, n

def refresh_all_pools():
    """Reconstrói os pools 1x por dia (90 por ocasião) e fatia em 30/30/30."""
    global LAST_BUILD_DAY, USED_TODAY
    global PRE_POOL, DURING_POOL, POST_POOL, GOODNIGHT_POOL
    global PRE_M, PRE_T, PRE_N, DURING_M, DURING_T, DURING_N, POST_M, POST_T, POST_N

    if today_br() == LAST_BUILD_DAY:
        return
    LAST_BUILD_DAY = today_br()
    USED_TODAY = {k: set() for k in USED_TODAY.keys()}

    # -------- PRE (cadastro/depósito/entrar)
    pre_pfx = [
        "{nome}, faltam minutos pra sessão —", "Partiu sessão!", "Hora da abertura —",
        "Últimos minutos —", "Chega junto —", "Vai começar —", "Atenção —",
        "Sem enrolar —", "Janela inicial chegando —", "Vem pro simples —",
        "Quem chega cedo vence —", "Convite direto —", "Reta final —",
        "Direto ao ponto —", "Tua vez —", "Sem desculpa —", "Bora pra prática —",
        "Momento certo —", "Alerta de início —", "Tá valendo —"
    ]
    pre_core = [
        "ativa tua conta, faz o primeiro depósito e entra no grupo.",
        "cria a conta e deixa a plataforma no gatilho.",
        "garante teu cadastro/depósito agora e abre o grupo.",
        "organiza a banca e cola na sessão com calma.",
        "deixa o acesso pronto pra pegar a primeira janela.",
        "conta ativa e banca pronta — o resto é execução.",
        "em 1 minuto resolve o acesso e vem pro grupo.",
        "acesso pronto hoje = execução tranquila agora.",
        "sem travar: cadastro e depósito feitos, bora operar.",
        "cria a conta, confirma o acesso e entra nas sessões.",
        "quem tá pronto pega os melhores pontos. Ativa e vem.",
        "chega pronto: conta ativa, grupo aberto e gestão.",
        "resolve o depósito agora e acompanha a abertura.",
        "o básico paga o dia: ativa e entra na sessão.",
        "não perde tempo — acesso pronto e partiu."
    ]
    pre_close = ["", " Bora.", " Vem.", " Agora.", " Sem drama.", " Faz e cola.", " Jogo simples.", " Partiu.", " Valendo.", " Te espero no grupo."]

    PRE_POOL = build_pool(pre_pfx, pre_core, pre_close, target=90)

    # -------- DURING (execução leve + acesso pronto)
    during_pfx = [
        "Sessão rolando —", "No ritmo —", "Calma e método —", "Sem FOMO —",
        "Confirmação primeiro —", "Ponto limpo > pressa —", "Na boa —",
        "Foco no simples —", "Cabeça fria —", "Processo acima de hype —",
        "Agora é execução —", "Olho na leitura —", "Nada de correria —"
    ]
    during_core = [
        "se ainda não ativou tua conta, resolve agora e acompanha a leitura.",
        "deixa teu acesso e depósito ok e segue o plano.",
        "se encaixar no teu plano, executa; se não, espera a próxima.",
        "acesso pronto te deixa leve na hora do clique.",
        "organiza a banca e protege o caixa.",
        "conta ativa + grupo aberto = execução sem correria.",
        "se travar, respira e ajusta. Acesso em dia ajuda.",
        "quem preparou o acesso joga no fácil.",
        "teu futuro curte disciplina. Prepara a base e vai.",
        "é método, não sorte. Deixa tudo pronto e acompanha.",
        "leitura confirma, depois o clique. Acesso pronto.",
        "sem improviso: confirma e só então entra.",
        "se a leitura sumiu, espera a próxima e mantém a calma."
    ]
    during_close = ["", " Sem pressa.", " É isso.", " Vai no básico.", " Bora na calma.", " Sem inventar.", " Tamo junto.", " Acompanha no grupo.", " Só o simples.", " Vambora."]

    DURING_POOL = build_pool(during_pfx, during_core, during_close, target=90)

    # -------- POST (fechamento de cada sessão)
    post_pfx = [
        "Sessão encerrada —", "Boa —", "Fechamos —", "Fim da janela —",
        "Organiza aí —", "Meta ou não —", "Na paz —", "Sem revenge —",
        "Planilha na mão —", "Respira —", "Foco no processo —", "Pra cima —"
    ]
    post_core = [
        "deixa tua conta/depósito em dia e volta no próximo horário pronto.",
        "anota dois pontos e garante o acesso pra próxima.",
        "estrutura hoje e colhe na próxima sessão.",
        "cadastro/depósito ok agora = execução tranquila depois.",
        "quem se organiza agora opera melhor depois.",
        "prepara a base: conta, grupo e gestão.",
        "resultado vem do básico bem-feito. Deixa tudo pronto.",
        "sem improviso amanhã — resolve hoje.",
        "te vejo na próxima janela. Chega pronto.",
        "o jogo é diário. Acesso ativo e cabeça fria.",
        "faz o simples entre as sessões: organizar e descansar.",
        "se faltou, resolve agora e volta focado."
    ]
    post_close = ["", " Simples assim.", " Bora.", " Fechou.", " Sem drama.", " Jogo limpo.", " Partiu próxima.", " É sobre método.", " Tamo junto.", " Até já."]

    POST_POOL = build_pool(post_pfx, post_core, post_close, target=90)

    # -------- GOOD NIGHT (22:30) – 90 únicas, sem fatiar
    night_pfx = [
        "Boa noite —", "Fechamos o dia —", "Encerramento —", "Fim do turno —",
        "Descansa —", "Amanhã tem sessão —", "Tudo certo —", "Rotina > hype —",
        "Processo é rei —", "Cabeça leve —", "Modo off —"
    ]
    night_core = [
        "deixa tua conta ativa e dorme tranquilo.",
        "organiza hoje, executa melhor amanhã.",
        "prepara o acesso e vem pra constância.",
        "nada de madrugada — volta focado amanhã.",
        "o mercado abre todo dia; quem vence chega pronto.",
        "o simples funciona: acesso pronto e gestão.",
        "tua consistência começa no preparo de hoje.",
        "planejamento noturno, execução diurna.",
        "sem ansiedade: estrutura primeiro, resultado depois.",
        "relaxa — amanhã a gente roda de novo.",
        "fecha tudo e vem zerado pra próxima."
    ]
    night_close = ["", " Até amanhã.", " Tamo junto.", " Boa.", " Bora repetir.", " É isso.", " Vamo pra cima amanhã.", " Só vem.", " Vai dar bom.", " Descansa."]

    GOODNIGHT_POOL = build_pool(night_pfx, night_core, night_close, target=90)

    # FATIA: 90 => 30/30/30 (manhã/tarde/noite) para pré/durante/pós
    global PRE_M, PRE_T, PRE_N, DURING_M, DURING_T, DURING_N, POST_M, POST_T, POST_N
    PRE_M, PRE_T, PRE_N = split_3x30(PRE_POOL)
    DURING_M, DURING_T, DURING_N = split_3x30(DURING_POOL)
    POST_M, POST_T, POST_N = split_3x30(POST_POOL)

    # Logs de verificação
    log.info(f"Pools atualizados ({LAST_BUILD_DAY})")
    log.info(f"PRE total: {len(PRE_POOL)} | M/T/N: {len(PRE_M)}/{len(PRE_T)}/{len(PRE_N)}")
    log.info(f"DURING total: {len(DURING_POOL)} | M/T/N: {len(DURING_M)}/{len(DURING_T)}/{len(DURING_N)}")
    log.info(f"POST total: {len(POST_POOL)} | M/T/N: {len(POST_M)}/{len(POST_T)}/{len(POST_N)}")
    log.info(f"GOOD_NIGHT total: {len(GOODNIGHT_POOL)}")

# monta pools no boot
refresh_all_pools()

def take_unique(kind_key: str, pool: list[str]) -> str:
    """
    Pega uma mensagem do pool (30 itens) sem repetir no dia para aquela 'kind_key'.
    kind_key: pre_m, pre_t, pre_n, during_m, during_t, during_n, post_m, post_t, post_n, goodnight
    """
    used = USED_TODAY[kind_key]
    for _ in range(len(pool)):
        m = random.choice(pool)
        if m not in used:
            used.add(m)
            return m
    used.clear()
    return random.choice(pool)

# ============== COPIES FIXAS ==============
WELCOME_TXT = "Opa, seja bem-vindo 😎 Me fala teu nome e já libero teu bônus!"
AFTER_NAME_TXT = "Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇"
SESSOES_TXT = (
    "⚡ Sessões do dia\n• 10:00\n• 15:00\n• 20:00\n\n"
    "🗓️ Cronograma semanal:\n• Segunda a Sexta: 10:00, 15:00, 20:00"
)

# ============== HANDLERS ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(WELCOME_TXT)
    return ASK_NAME

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    nome = update.message.text.strip()
    USERS[chat_id] = nome
    SUBSCRIBERS.add(chat_id)

    await update.message.reply_text(AFTER_NAME_TXT.format(nome=nome))
    if PDF_URL:
        try:
            await context.bot.send_document(
                chat_id=chat_id,
                document=PDF_URL,
                caption="📄 Guia Oráculo Black — seu material de início!"
            )
        except Exception as e:
            log.warning(f"Falha ao enviar PDF: {e}")

    if LINK_CAD:
        txt = "**CLIQUE AQUI** para receber 10.000 e começar a operar agora mesmo:"
        await context.bot.send_message(chat_id=chat_id, text=f"{txt}\n{LINK_CAD}", parse_mode=ParseMode.MARKDOWN)

    await context.bot.send_message(
        chat_id=chat_id,
        text="Atalhos rápidos pra começar 👇",
        reply_markup=fixed_shortcuts_keyboard()
    )
    return ConversationHandler.END

async def sessoes_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(SESSOES_TXT)

# ============== BROADCAST ==========
async def _broadcast(context: ContextTypes.DEFAULT_TYPE, pool: list[str], kind_key: str, tag: str):
    # rebuild diário se virou o dia
    if today_br() != LAST_BUILD_DAY:
        refresh_all_pools()
    if not SUBSCRIBERS:
        return

    raw = take_unique(kind_key, pool)
    for chat_id in list(SUBSCRIBERS):
        try:
            msg = personalize(raw, chat_id)
            msg = maybe_emoji(msg)
            await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=cta_keyboard())
        except Exception as e:
            log.warning(f"Falha ao enviar ({tag}) para {chat_id}: {e}")

# PRÉ (30 por horário)
async def pre_morning(ctx):   await _broadcast(ctx, PRE_M, "pre_m", "pre_morning")
async def pre_afternoon(ctx): await _broadcast(ctx, PRE_T, "pre_t", "pre_afternoon")
async def pre_night(ctx):     await _broadcast(ctx, PRE_N, "pre_n", "pre_night")

# DURANTE (2–3 mensagens por janela, usando o pool do horário)
async def during_burst(ctx, tag):
    if tag == "morning":
        pool, key = DURING_M, "during_m"
    elif tag == "afternoon":
        pool, key = DURING_T, "during_t"
    else:
        pool, key = DURING_N, "during_n"

    n = random.randint(2, 3)
    for _ in range(n):
        await _broadcast(ctx, pool, key, f"during_{tag}")
        await asyncio.sleep(random.randint(180, 420))  # 3–7 min

# PÓS (30 por horário)
async def post_morning(ctx):   await _broadcast(ctx, POST_M, "post_m", "post_morning")
async def post_afternoon(ctx): await _broadcast(ctx, POST_T, "post_t", "post_afternoon")
async def post_night(ctx):     await _broadcast(ctx, POST_N, "post_n", "post_night")

# BOA NOITE (22:30 – usa pool único de 90)
async def good_night(ctx):     await _broadcast(ctx, GOODNIGHT_POOL, "goodnight", "good_night")

# ============== SCHEDULE ==============
def schedule_daily_jobs(app: Application):
    jq = getattr(app, "job_queue", None)
    if jq is None:
        raise RuntimeError("JobQueue indisponível. Confirme PTB 21.3 no requirements.")

    # Pré (jitter ±5)
    jq.run_daily(pre_morning,   time=jitter(br_time(9, 50), 5, 5),   name="pre_morning")
    jq.run_daily(pre_afternoon, time=jitter(br_time(14, 50), 5, 5),  name="pre_afternoon")
    jq.run_daily(pre_night,     time=jitter(br_time(19, 50), 5, 5),  name="pre_night")

    # Durante (burst por horário)
    jq.run_daily(lambda c: during_burst(c, "morning"),   time=br_time(10, 0), name="during_morning")
    jq.run_daily(lambda c: during_burst(c, "afternoon"), time=br_time(15, 0), name="during_afternoon")
    jq.run_daily(lambda c: during_burst(c, "night"),     time=br_time(20, 0), name="during_night")

    # Pós (jitter ±5)
    jq.run_daily(post_morning,   time=jitter(br_time(10, 40), 5, 5), name="post_morning")
    jq.run_daily(post_afternoon, time=jitter(br_time(15, 40), 5, 5), name="post_afternoon")
    jq.run_daily(post_night,     time=jitter(br_time(21, 0),  5, 5), name="post_night")

    # Boa noite
    jq.run_daily(good_night, time=br_time(22, 30), name="good_night")

# ============== MAIN ==============
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não encontrado nas variáveis de ambiente.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(sessoes_btn, pattern="^sessoes$"))

    schedule_daily_jobs(app)
    log.info("Bot iniciado. Agendadores ativos (BR -03:00).")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
