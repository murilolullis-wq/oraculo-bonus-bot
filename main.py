import os, random, logging, asyncio, pickle
from datetime import datetime, date, time, timedelta
import pytz

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder, Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
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
PDF_URL    = os.getenv("PDF_URL", "")     # PDF bônus (URL pública)
GROUP_LINK = os.getenv("GROUP_LINK", "")  # link do grupo (opcional)

TZ = pytz.timezone("America/Sao_Paulo")

# ============== PERSISTÊNCIA ==============
STATE_FILE = "oraculo_state.pickle"
SUBSCRIBERS: set[int] = set()
USERS: dict[int, str] = {}  # chat_id -> nome

def load_state():
    global SUBSCRIBERS, USERS
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                data = pickle.load(f)
            SUBSCRIBERS = set(data.get("subs", []))
            USERS = dict(data.get("users", {}))
            log.info(f"State carregado: subs={len(SUBSCRIBERS)}, users={len(USERS)}")
        except Exception as e:
            log.warning(f"Falha ao carregar state: {e}")

def save_state():
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"subs": list(SUBSCRIBERS), "users": USERS}, f)
    except Exception as e:
        log.warning(f"Falha ao salvar state: {e}")

load_state()

# ============== CONTROLES DIÁRIOS ==============
LAST_BUILD_DAY: date = date.min
USED_TODAY: dict[str, set[str]] = {
    # pre/during/post: m/t/n   | goodnight: pool único
    "pre_m": set(), "pre_t": set(), "pre_n": set(),
    "dur_m": set(), "dur_t": set(), "dur_n": set(),
    "pos_m": set(), "pos_t": set(), "pos_n": set(),
    "boa": set(),
}

# ============== HELPERS ==============
EMOJIS = ["💰","🔥","📈","⚡","🚀","📊","💎","😎","💥","🏆"]

def today_br() -> date:
    return datetime.now(TZ).date()

def maybe_emoji(txt: str) -> str:
    return f"{txt} {random.choice(EMOJIS)}" if random.random() < 0.60 else txt

def name_of(chat_id: int) -> str:
    return USERS.get(chat_id, "").strip()

def personalize(raw: str, chat_id: int, hora: str) -> str:
    nome = name_of(chat_id) or "você"
    return raw.replace("{nome}", nome).replace("{hora}", hora)

def br_time(h: int, m: int = 0) -> time:
    return time(h, m, tzinfo=TZ)

def jitter(t: time, minus=5, plus=5) -> time:
    now = datetime.now(TZ)
    base = TZ.localize(datetime(now.year, now.month, now.day, t.hour, t.minute))
    j = random.randint(-minus, plus)
    return (base + timedelta(minutes=j)).timetz()

# ===== CTA dinâmico: se texto marcar <<GRUPO>>, usar só botão do grupo =====
def cta_keyboard_from_text(texto: str) -> InlineKeyboardMarkup:
    is_grupo = "<<GRUPO>>" in texto
    rows = []
    if is_grupo and GROUP_LINK:
        rows.append([InlineKeyboardButton("✅ ABRIR GRUPO", url=GROUP_LINK)])
    else:
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
        if GROUP_LINK and random.random() < 0.5:
            rows.append([InlineKeyboardButton("✅ ABRIR GRUPO", url=GROUP_LINK)])
    if LINK_VIDEO and random.random() < 0.4:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    return InlineKeyboardMarkup(rows)

def fixed_shortcuts_keyboard() -> InlineKeyboardMarkup:
    rows = []
    if LINK_VIDEO:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
    rows.append([InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")])
    if GROUP_LINK:
        rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    return InlineKeyboardMarkup(rows)

# ===== PDF (local -> URL -> link) =====
async def send_bonus_pdf(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    caption = "📄 Guia Oráculo Black — seu material de início!"
    local_path = "guia_oraculo_black.pdf"

    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                await context.bot.send_document(chat_id=chat_id, document=InputFile(f, filename="guia_oraculo_black.pdf"), caption=caption)
                return True
        except Exception as e:
            log.warning(f"PDF local falhou: {e}")

    if PDF_URL:
        try:
            await context.bot.send_document(chat_id=chat_id, document=PDF_URL, caption=caption)
            return True
        except Exception as e:
            log.warning(f"PDF URL falhou: {e}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n{PDF_URL}")
            return True
        except Exception as e:
            log.warning(f"PDF link texto falhou: {e}")
    return False

# ============== POOLS (90 por ocasião; 30 boa-noite) ==============
def build_pool_pre() -> list[str]:
    bases = [
        # Marca <<GRUPO>> quando o call to action correto é abrir grupo.
        "<<GRUPO>> {nome}, bora pra sessão das {hora} — entra no grupo agora e chega pronto.",
        "<<GRUPO>> {nome}, sem enrolar: sessão {hora} já já — entra no grupo e vem.",
        "{nome}, partiu sessão das {hora}! Ativa tua conta e deixa tudo pronto.",
        "{nome}, últimos minutos pra sessão {hora} — cadastro/depósito feitos e bora.",
        "Atenção {nome}: {hora} a gente abre a sessão. Chega pronto e sem correria.",
        "{nome}, quem chega cedo pega os melhores pontos na sessão das {hora}.",
        "{nome}, bora pra prática? Sessão {hora} — conta ativa e foco no simples.",
        "{nome}, sessão {hora} chegando… prepara a banca e entra sem pressa.",
        "{nome}, {hora} é nossa janela. Garante o acesso e cola.",
        "Direto ao ponto, {nome}: sessão das {hora}. Resolve o básico e vem.",
        "{nome}, tua vez hoje às {hora}. Não deixa pra depois.",
        "{nome}, {hora} abre. Conta ativa, depósito ok e grupo aberto.",
        "{nome}, chegou a hora: {hora}. Faça o básico e vem pro jogo.",
        "{nome}, {hora} é hora boa. Chega pronto.",
        "<<GRUPO>> {nome}, vem pro grupo antes da sessão das {hora} pra não perder o começo.",
    ]
    # Expande variando verbos de ação / fechamentos até dar 90
    closes = ["", " Bora.", " Vem.", " Agora.", " Sem drama.", " Jogo simples.", " Partiu.", " Valendo."]
    cores = []
    for b in bases:
        for c in closes:
            cores.append((b + c).strip())
    random.shuffle(cores)
    return cores[:90] if len(cores) >= 90 else (cores * ((90 // max(1, len(cores))) + 1))[:90]

def build_pool_during() -> list[str]:
    bases = [
        "Sessão {hora} rolando — {nome}, confirma leitura, depois executa.",
        "{nome}, no ritmo da sessão {hora}. Nada de correria — método > pressa.",
        "Agora é execução, {nome}. Se encaixar no plano, vai — é sessão {hora}.",
        "Sem FOMO, {nome}. Se a leitura sumiu, espera a próxima (sessão {hora}).",
        "Ponto limpo > pressa — {nome}, acompanha a sessão {hora} com calma.",
        "<<GRUPO>> {nome}, tá on a sessão {hora}. Entra no grupo pra acompanhar ao vivo.",
        "Confirmação primeiro, clique depois — {nome}, sessão {hora}.",
        "{nome}, acesso pronto te deixa leve na hora do clique. Sessão {hora}.",
        "Foco no simples, {nome}. Sessão {hora} segue.",
        "{nome}, lê o movimento e protege a banca. Sessão {hora}.",
        "Nada de inventar, {nome}. Sessão {hora} pede disciplina.",
        "<<GRUPO>> {nome}, vem pro grupo acompanhar a sessão {hora} sem perder os pontos.",
    ]
    closes = ["", " É isso.", " Sem pressa.", " Só o simples.", " Bora na calma.", " Tamo junto."]
    cores = []
    for b in bases:
        for c in closes:
            cores.append((b + c).strip())
    random.shuffle(cores)
    return cores[:90] if len(cores) >= 90 else (cores * ((90 // max(1, len(cores))) + 1))[:90]

def build_pool_post() -> list[str]:
    bases = [
        "Sessão {hora} encerrada — boa, {nome}! Prepara a próxima e segue leve.",
        "Fechamos a {hora}. {nome}, anota os pontos e volta pronto depois.",
        "Fim da janela {hora}. {nome}, organiza a banca e mantém o processo.",
        "Sem revenge, {nome}. Sessão {hora} foi. Foco no plano.",
        "<<GRUPO>> {nome}, confere o recap no grupo e já te ajeita pra próxima.",
        "Resultado vem do básico bem-feito. {nome}, {hora} entregue.",
        "Se faltou, {nome}, resolve agora e volta focado na próxima janela.",
        "Planilha na mão e cabeça fria — {nome}, {hora} entregue.",
        "Pra cima, {nome}. {hora} foi. Próxima janela a caminho.",
        "Simples assim, {nome}. Sessão {hora} concluída.",
    ]
    closes = ["", " Tamo junto.", " Partiu próxima.", " Boa.", " Até já.", " Jogo limpo."]
    cores = []
    for b in bases:
        for c in closes:
            cores.append((b + c).strip())
    random.shuffle(cores)
    return cores[:90] if len(cores) >= 90 else (cores * ((90 // max(1, len(cores))) + 1))[:90]

def build_pool_goodnight() -> list[str]:
    bases = [
        "Boa noite, {nome}. Amanhã tem sessão — chega pronto.",
        "Encerramos o dia, {nome}. Prepara a base e descansa.",
        "Fim do turno, {nome}. A consistência começa no preparo.",
        "Descansa, {nome}. Amanhã a gente roda de novo.",
        "Rotina vence hype, {nome}. Amanhã tem {hora} de novo.",
        "Cabeça leve, {nome}. Planeja hoje, executa amanhã.",
        "Processo é rei, {nome}. Fecha tudo e vem zerado amanhã.",
        "Tudo certo por hoje, {nome}. Amanhã tem mais.",
        "Sem ansiedade, {nome}. Estrutura primeiro, resultado depois.",
        "Fecha com paz, {nome}. Até amanhã.",
    ]
    closes = ["", " Boa.", " Tamo junto.", " Até amanhã.", " Descansa.", " Vamo pra cima amanhã."]
    out = []
    for b in bases:
        for c in closes:
            out.append((b + " " + c).strip())
    random.shuffle(out)
    return out[:30] if len(out) >= 30 else (out * ((30 // max(1, len(out))) + 1))[:30]

# pools fatiados: 90 => 30/30/30
PRE_M: list[str] = []
PRE_T: list[str] = []
PRE_N: list[str] = []
DUR_M: list[str] = []
DUR_T: list[str] = []
DUR_N: list[str] = []
POS_M: list[str] = []
POS_T: list[str] = []
POS_N: list[str] = []
BOA:   list[str] = []

def refresh_all_pools(force=False):
    global LAST_BUILD_DAY, USED_TODAY
    global PRE_M, PRE_T, PRE_N, DUR_M, DUR_T, DUR_N, POS_M, POS_T, POS_N, BOA

    if not force and today_br() == LAST_BUILD_DAY:
        return
    LAST_BUILD_DAY = today_br()
    USED_TODAY = {k: set() for k in USED_TODAY.keys()}

    pre_pool = build_pool_pre()
    dur_pool = build_pool_during()
    pos_pool = build_pool_post()
    boa_pool = build_pool_goodnight()

    PRE_M, PRE_T, PRE_N = pre_pool[0:30], pre_pool[30:60], pre_pool[60:90]
    DUR_M, DUR_T, DUR_N = dur_pool[0:30], dur_pool[30:60], dur_pool[60:90]
    POS_M, POS_T, POS_N = pos_pool[0:30], pos_pool[30:60], pos_pool[60:90]
    BOA = boa_pool

    log.info(f"Pools {LAST_BUILD_DAY} -> PRE/DUR/POS: 90/90/90 (30x cada) | BOA: {len(BOA)}")

refresh_all_pools(force=True)

def take_unique(kind: str, pool: list[str]) -> str:
    used = USED_TODAY[kind]
    for _ in range(len(pool)):
        s = random.choice(pool)
        if s not in used:
            used.add(s)
            return s
    used.clear()
    return random.choice(pool)

# ============== COPIES FIXAS ==============
WELCOME_TXT = "Opa, seja bem-vindo 😎 Me fala teu nome e já libero teu bônus!"
AFTER_NAME_TXT = "Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇"
SESSOES_TXT = "⚡ Sessões do dia\n• 10:00\n• 15:00\n• 20:00"

# ============== HANDLERS BÁSICOS ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(WELCOME_TXT)

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    chat_id = update.effective_chat.id
    texto = (update.message.text or "").strip()
    # já tem nome? ignora
    if chat_id in USERS and USERS[chat_id]:
        return
    if not texto:
        return
    USERS[chat_id] = texto
    SUBSCRIBERS.add(chat_id)
    save_state()

    await update.message.reply_text(AFTER_NAME_TXT.format(nome=texto))
    await send_bonus_pdf(context, chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Atalhos rápidos pra começar 👇",
        reply_markup=fixed_shortcuts_keyboard()
    )

async def sessoes_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(SESSOES_TXT)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong ✅")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comando não reconhecido. Manda /start pra liberar teu bônus 😉")

# ============== BROADCAST SCHEDULED ==============
# Horários oficiais e labels
HORAS = {"m":"10:00", "t":"15:00", "n":"20:00"}

async def _broadcast(context: ContextTypes.DEFAULT_TYPE, pool: list[str], used_key: str, hora_str: str):
    if today_br() != LAST_BUILD_DAY:
        refresh_all_pools()
    if not SUBSCRIBERS:
        return
    raw = take_unique(used_key, pool)
    # se a mensagem marca <<GRUPO>>, CTA só do grupo
    is_grupo = "<<GRUPO>>" in raw
    clean = raw.replace("<<GRUPO>>", "")
    for chat_id in list(SUBSCRIBERS):
        try:
            txt = personalize(clean, chat_id, hora_str)
            txt = maybe_emoji(txt)
            await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=cta_keyboard_from_text(raw))
        except Exception as e:
            log.warning(f"Falha broadcast {used_key} -> {chat_id}: {e}")

# Pré (30 por horário)
async def pre_m(ctx): await _broadcast(ctx, PRE_M, "pre_m", HORAS["m"])
async def pre_t(ctx): await _broadcast(ctx, PRE_T, "pre_t", HORAS["t"])
async def pre_n(ctx): await _broadcast(ctx, PRE_N, "pre_n", HORAS["n"])

# Durante (2–3 mensagens com intervalos)
async def during_burst(ctx, tag):
    if tag=="m": pool, key, hora = DUR_M, "dur_m", HORAS["m"]
    elif tag=="t": pool, key, hora = DUR_T, "dur_t", HORAS["t"]
    else: pool, key, hora = DUR_N, "dur_n", HORAS["n"]
    n = random.randint(2,3)
    for _ in range(n):
        await _broadcast(ctx, pool, key, hora)
        await asyncio.sleep(random.randint(180, 420))  # 3–7 min

# Pós
async def post_m(ctx): await _broadcast(ctx, POS_M, "pos_m", HORAS["m"])
async def post_t(ctx): await _broadcast(ctx, POS_T, "pos_t", HORAS["t"])
async def post_n(ctx): await _broadcast(ctx, POS_N, "pos_n", HORAS["n"])

# Boa-noite (30 no pool total)
async def boa_noite(ctx): await _broadcast(ctx, BOA, "boa", "amanhã")

# ============== TESTES (disparam na hora) ==============
async def test_pre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id); save_state(); await pre_m(context)

async def test_dur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id); save_state(); await during_burst(context, "m")

async def test_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id); save_state(); await post_m(context)

async def test_noite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id); save_state(); await boa_noite(context)

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.add(update.effective_chat.id); save_state()
    await pre_m(context); await asyncio.sleep(1)
    await during_burst(context, "m"); await asyncio.sleep(1)
    await post_m(context); await asyncio.sleep(1)
    await boa_noite(context)

# ============== SCHEDULE ==============
def schedule_jobs(app: Application):
    jq = app.job_queue
    if jq is None:
        raise RuntimeError("JobQueue indisponível.")

    # Pré (com jitter ±5 min)
    jq.run_daily(pre_m, time=jitter(br_time(9,50)),  name="pre_m")
    jq.run_daily(pre_t, time=jitter(br_time(14,50)), name="pre_t")
    jq.run_daily(pre_n, time=jitter(br_time(19,50)), name="pre_n")

    # Durante (burst)
    jq.run_daily(lambda c: during_burst(c,"m"), time=br_time(10,0), name="dur_m")
    jq.run_daily(lambda c: during_burst(c,"t"), time=br_time(15,0), name="dur_t")
    jq.run_daily(lambda c: during_burst(c,"n"), time=br_time(20,0), name="dur_n")

    # Pós (com jitter ±5)
    jq.run_daily(post_m, time=jitter(br_time(10,40)), name="pos_m")
    jq.run_daily(post_t, time=jitter(br_time(15,40)), name="pos_t")
    jq.run_daily(post_n, time=jitter(br_time(21,0)),  name="pos_n")

    # Boa-noite (22:30)
    jq.run_daily(boa_noite, time=br_time(22,30), name="boa_noite")

# ============== MAIN ==============
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não encontrado nas variáveis de ambiente.")

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers simples e à prova de bala
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, got_name))
    app.add_handler(CallbackQueryHandler(sessoes_btn, pattern="^sessoes$"))

    # Testes
    app.add_handler(CommandHandler("ping",  ping))
    app.add_handler(CommandHandler("teste_pre", test_pre))
    app.add_handler(CommandHandler("teste_durante", test_dur))
    app.add_handler(CommandHandler("teste_pos", test_pos))
    app.add_handler(CommandHandler("teste_noite", test_noite))
    app.add_handler(CommandHandler("teste", test_all))

    # Catch-all pra comandos desconhecidos
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    schedule_jobs(app)
    log.info("Bot iniciado. Agendadores ativos (BR -03:00).")
    app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

if __name__ == "__main__":
    main()
