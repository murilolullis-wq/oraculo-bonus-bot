import os, random, logging, asyncio, pickle
from datetime import datetime, date, time, timedelta
import pytz

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.ext import (
    ApplicationBuilder, Application, CommandHandler,
    MessageHandler, CallbackQueryHandler, ContextTypes, filters
)

# ================= LOG =================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("oraculo-bonus-bot")

# ============== ENV VARS ==============
BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
LINK_CAD   = os.getenv("LINK_CAD", "")
LINK_VIDEO = os.getenv("LINK_VIDEO", "")
PDF_URL    = os.getenv("PDF_URL", "")
GROUP_LINK = os.getenv("GROUP_LINK", "")

if not BOT_TOKEN:
    raise RuntimeError("Falta BOT_TOKEN nas variáveis de ambiente.")

TZ = pytz.timezone("America/Sao_Paulo")

# ============== PERSISTÊNCIA ==============
STATE_FILE = "oraculo_state.pickle"
SUBSCRIBERS: set[int] = set()
USERS: dict[int, str] = {}

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

def cta_keyboard_from_text(texto: str) -> InlineKeyboardMarkup:
    is_grupo = "<<GRUPO>>" in texto
    rows = []
    if is_grupo and GROUP_LINK:
        rows.append([InlineKeyboardButton("✅ ABRIR GRUPO", url=GROUP_LINK)])
    else:
        if LINK_CAD:
            rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
        if GROUP_LINK and random.random() < 0.5:
            rows.append([InlineKeyboardButton("✅ ABRIR GRUPO", url=GROUP_LINK)])
    if LINK_VIDEO and random.random() < 0.4:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")]])

def fixed_shortcuts_keyboard() -> InlineKeyboardMarkup:
    rows = []
    if LINK_VIDEO:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    if LINK_CAD:
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
    rows.append([InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")])
    if GROUP_LINK:
        rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    return InlineKeyboardMarkup(rows)

async def send_bonus_pdf(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    caption = "📄 Guia Oráculo Black — seu material de início!"
    local_path = "guia_oraculo_black.pdf"
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(f, filename="guia_oraculo_black.pdf"),
                    caption=caption
                )
                return True
        except Exception:
            pass
    if PDF_URL:
        try:
            await context.bot.send_document(chat_id=chat_id, document=PDF_URL, caption=caption)
            return True
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"{caption}\n{PDF_URL}")
            return True
    return False

# ============== INTENT CAPTURE ==============
INTENT_PATTERNS = {
    "cadastro": [
        "cadastrar","cadastro","registrar","registro","abrir conta",
        "como entro","quero entrar","link","começar","iniciar",
        "depósito","deposito","depositar","banca","saldo","pagar"
    ],
    "grupo": [
        "grupo","canal","telegram","abrir grupo","entrar no grupo","acessar grupo"
    ],
    "video": ["video","vídeo","explicativo","tutorial"],
    "sessoes": ["sessao","sessão","horario","horário","que horas","agenda","cronograma"],
}

def _match_intent(txt: str):
    t = (txt or "").lower()
    for intent, kws in INTENT_PATTERNS.items():
        for k in kws:
            if k in t:
                return intent
    return None

async def handle_intent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nome = name_of(chat_id) or "você"
    intent = _match_intent(update.message.text)
    if not intent:
        return
    if intent == "cadastro" and LINK_CAD:
        txt = maybe_emoji(f"{nome}, segue o acesso pra começar agora. Resolve cadastro/depósito e cola na sessão.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)]])
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb)
    elif intent == "grupo" and GROUP_LINK:
        txt = maybe_emoji(f"{nome}, entra no grupo pra acompanhar AO VIVO.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ABRIR GRUPO", url=GROUP_LINK)]])
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb)
    elif intent == "video" and LINK_VIDEO:
        txt = maybe_emoji(f"{nome}, vê o vídeo explicativo rapidinho e já começa.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)]])
        await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=kb)
    elif intent == "sessoes":
        await context.bot.send_message(chat_id=chat_id, text=SESSOES_TXT)

# ============== MENSAGENS (90 por ocasião) ==============
def build_pool(base, closes, mult=90):
    pool = [(b + " " + c).strip() for b in base for c in closes]
    random.shuffle(pool)
    return (pool * ((mult // len(pool)) + 1))[:mult]

def pre_msgs():  # pré sessão
    return build_pool(
        [
            "<<GRUPO>> {nome}, bora pra sessão das {hora}.",
            "{nome}, partiu sessão das {hora}.",
            "{nome}, chegou a hora {hora}. Bora.",
            "{nome}, garante teu acesso antes da {hora}.",
            "Janela {hora} chegando, {nome}. Se posiciona.",
            "{nome}, lembra do básico na {hora}. Sem pressa.",
        ],
        ["", "🔥", "⚡", " Bora.", " Sem drama.", " Vem pro grupo."]
    )

def dur_msgs():  # durante sessão (com botão do grupo em alguns)
    return build_pool(
        [
            "Sessão {hora} rolando — {nome}, foco no simples.",
            "<<GRUPO>> {nome}, entra no grupo pra acompanhar a sessão {hora}.",
            "{nome}, confirma leitura antes de executar. {hora}.",
            "Fluxo da {hora} em andamento. {nome}, protege a banca.",
            "{nome}, deixa rodar só o necessário. Sessão {hora}.",
            "Sem ansiedade, {nome}. Segue o plano. {hora}.",
        ],
        ["", " É isso.", " Sem pressa.", " Bora na calma.", " Vem pro grupo."]
    )

def pos_msgs():  # pós sessão
    return build_pool(
        [
            "Sessão {hora} encerrada — boa, {nome}.",
            "Fim da janela {hora}. {nome}, organiza a banca.",
            "<<GRUPO>> {nome}, confere o recap no grupo.",
            "Anota os pontos da {hora}, {nome}. Evolução diária.",
            "{nome}, sem giro extra. Disciplina pós {hora}.",
            "Deu bom, {nome}. Fecha e respira. {hora} concluída.",
        ],
        ["", " Tamo junto.", " Partiu próxima.", " Boa.", " Só o simples."]
    )

def boa_msgs():  # boa noite (30)
    return build_pool(
        [
            "Boa noite, {nome}. Amanhã tem sessão.",
            "Encerramos o dia, {nome}. Prepara a base.",
            "Descansa, {nome}. Amanhã é outra rodada.",
            "{nome}, constância > intensidade. Até amanhã.",
            "Fecha o dia no verde mental, {nome}. Boa noite.",
        ],
        ["", " Tamo junto.", " Até amanhã.", " Vamo pra cima."],
        30
    )

PRE_M, DUR_M, POS_M, BOA = pre_msgs(), dur_msgs(), pos_msgs(), boa_msgs()
# Reuso pro T e N (baseadas no mesmo estilo)
PRE_T, DUR_T, POS_T = PRE_M, DUR_M, POS_M
PRE_N, DUR_N, POS_N = PRE_M, DUR_M, POS_M

# ============== BROADCASTS & TESTES ==============
HORAS = {"m": "08:00", "t": "15:00", "n": "20:00"}

async def _broadcast(context, pool, used_key, hora):
    for chat_id in list(SUBSCRIBERS):
        try:
            raw = random.choice(pool)
            msg = personalize(raw.replace("<<GRUPO>>", ""), chat_id, hora)
            kb = cta_keyboard_from_text(raw)
            await context.bot.send_message(chat_id=chat_id, text=maybe_emoji(msg), reply_markup=kb)
        except Exception as e:
            log.warning(f"Falha broadcast {used_key}: {e}")

async def pre_m(c): await _broadcast(c, PRE_M, "pre_m", HORAS["m"])
async def pre_t(c): await _broadcast(c, PRE_T, "pre_t", HORAS["t"])
async def pre_n(c): await _broadcast(c, PRE_N, "pre_n", HORAS["n"])

async def during_burst(c, tag):
    pool = DUR_M if tag == "m" else DUR_T if tag == "t" else DUR_N
    hora = HORAS[tag]
    n = random.randint(2, 3)
    for _ in range(n):
        await _broadcast(c, pool, f"dur_{tag}", hora)
        await asyncio.sleep(random.randint(180, 480))  # 3–8 min

async def post_m(c): await _broadcast(c, POS_M, "pos_m", HORAS["m"])
async def post_t(c): await _broadcast(c, POS_T, "pos_t", HORAS["t"])
async def post_n(c): await _broadcast(c, POS_N, "pos_n", HORAS["n"])
async def boa_noite(c): await _broadcast(c, BOA, "boa", "amanhã")

# ======= Teste individual (só pra quem chamou) =======
async def _send_to(context, chat_id: int, raw: str, hora: str):
    txt = personalize(raw.replace("<<GRUPO>>", ""), chat_id, hora)
    await context.bot.send_message(chat_id=chat_id, text=maybe_emoji(txt), reply_markup=cta_keyboard_from_text(raw))

async def test_sequence_for_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        # pré
        await _send_to(context, chat_id, random.choice(PRE_M), HORAS["m"])
        await asyncio.sleep(1)
        # durante (2–3 msgs espaçadas)
        n = random.randint(2, 3)
        for _ in range(n):
            await _send_to(context, chat_id, random.choice(DUR_M), HORAS["m"])
            await asyncio.sleep(random.randint(180, 480))
        # pós
        await _send_to(context, chat_id, random.choice(POS_M), HORAS["m"])
        await asyncio.sleep(1)
        # boa noite
        await _send_to(context, chat_id, random.choice(BOA), "amanhã")
    except Exception as e:
        log.error(f"Teste seq user erro: {e}")

# ============== SCHEDULES ==============
def schedule_jobs(app: Application):
    jq = app.job_queue
    # MANHÃ 08:00
    jq.run_daily(pre_m, time=jitter(br_time(7, 50)))
    jq.run_daily(lambda c: during_burst(c, "m"), time=br_time(8, 0))
    jq.run_daily(post_m, time=jitter(br_time(8, 40)))
    # TARDE 15:00
    jq.run_daily(pre_t, time=jitter(br_time(14, 50)))
    jq.run_daily(lambda c: during_burst(c, "t"), time=br_time(15, 0))
    jq.run_daily(post_t, time=jitter(br_time(15, 40)))
    # NOITE 20:00
    jq.run_daily(pre_n, time=jitter(br_time(19, 50)))
    jq.run_daily(lambda c: during_burst(c, "n"), time=br_time(20, 0))
    jq.run_daily(post_n, time=jitter(br_time(21, 0)))
    # BOA NOITE
    jq.run_daily(boa_noite, time=br_time(22, 30))

# ============== FLUXOS / COMANDOS ==============
WELCOME_TXT = "Opa, seja bem-vindo 😎 Me fala teu nome e já libero teu bônus!"
AFTER_NAME_TXT = "Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇"
SESSOES_TXT = "⚡ Sessões do dia\n• 08:00\n• 15:00\n• 20:00"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(WELCOME_TXT)

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    texto = (update.message.text or "").strip()

    # Se já tem nome salvo → vira captação
    if chat_id in USERS and USERS[chat_id]:
        await handle_intent(update, context)
        return

    # Onboarding
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

# /teste: ACK + execução em background para o próprio usuário
async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    SUBSCRIBERS.add(chat_id)
    save_state()
    await update.message.reply_text("✅ Vou disparar os testes agora (pré, durante, pós e boa noite)...")

    async def run_tests():
        await test_sequence_for_user(context, chat_id)

    asyncio.get_event_loop().create_task(run_tests())

# ============== MAIN ==============
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(sessoes_btn, pattern="^sessoes$"))
    app.add_handler(CommandHandler("teste", test_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, got_name))

    schedule_jobs(app)
    log.info("Bot iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

if __name__ == "__main__":
    main()
