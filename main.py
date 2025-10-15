import os
import json
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters, PicklePersistence
)

# ================== CONFIG ==================
BOT_TOKEN  = os.getenv("BOT_TOKEN")
PDF_URL    = os.getenv("PDF_URL", "./guia_oraculo_black.pdf")  # URL pública ou caminho local
LINK_CAD   = os.getenv("LINK_CAD", "https://example.com/cadastro")
LINK_VIDEO = os.getenv("LINK_VIDEO", "https://t.me/seu_canal/1")
MSG_FILE   = os.getenv("MSG_FILE", "mensagens.json")
FILE_ID    = os.getenv("FILE_ID", "").strip()  # <- quando preencher, envio do PDF fica instantâneo
ADMIN_ID   = os.getenv("ADMIN_ID", "").strip()  # opcional: seu user_id para receber alertas

TZ = ZoneInfo("America/Sao_Paulo")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("oraculo-bot-pro")

# ================== LOAD MESSAGES ==================
def load_messages():
    try:
        with open(MSG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            pools = data.get("pools", {})
            if not pools:
                raise ValueError("Arquivo JSON sem chave 'pools'.")
            return pools
    except Exception as e:
        log.error(f"Erro ao carregar {MSG_FILE}: {e}")
        return {}

POOLS = load_messages()

# ================== BUTTONS ==================
def botoes_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)],
        [InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)],
        [InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")]
    ])

def botao_comecar_agora():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)]])

# ================== HELPERS ==================
def week_key():
    iso = datetime.now(TZ).isocalendar()
    return f"{iso.year}-W{iso.week}"

def choose_variant(pool_name, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> str:
    templates = POOLS.get(pool_name, [])
    if not templates:
        return ""
    bot_data = context.application.bot_data.setdefault("tracker", {})
    wk = week_key()
    chat_track = bot_data.setdefault(chat_id, {})
    pool = chat_track.setdefault(pool_name, {"week": wk, "used": set()})
    if pool["week"] != wk:
        pool["week"] = wk
        pool["used"] = set()
    import random
    available = [i for i in range(len(templates)) if i not in pool["used"]]
    if not available:
        pool["used"] = set()
        available = list(range(len(templates)))
    idx = random.choice(available)
    pool["used"].add(idx)
    return templates[idx]

async def send_from_pool(pool_name, context: ContextTypes.DEFAULT_TYPE, chat_id: int, hora=None):
    """Mensagem agendada + botão 'Começar Agora'."""
    txt = choose_variant(pool_name, context, chat_id)
    if not txt:
        return
    nome = (context.user_data.get("nome") or "").strip() if hasattr(context, "user_data") else ""
    txt = txt.format(hora=hora or "", nome=nome, link=LINK_CAD)
    await context.bot.send_message(chat_id, txt, reply_markup=botao_comecar_agora())

async def send_bonus_pdf(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Envia o PDF. Usa FILE_ID se existir (instantâneo); senão envia e registra o file_id."""
    caption = "📄 Guia Oráculo Black — o seu bônus de início!"
    global FILE_ID

    try:
        # 1) Se já temos FILE_ID (env var), envio é instantâneo
        if FILE_ID:
            await context.bot.send_document(chat_id=chat_id, document=FILE_ID, caption=caption)
            return

        # 2) Caso contrário, envia (URL pública ou arquivo local) e captura o file_id
        if str(PDF_URL).startswith(("http://", "https://")):
            msg = await context.bot.send_document(chat_id=chat_id, document=PDF_URL, caption=caption)
        else:
            with open(PDF_URL, "rb") as f:
                msg = await context.bot.send_document(chat_id=chat_id, document=f,
                                                      filename=os.path.basename(PDF_URL), caption=caption)
        if msg and msg.document and msg.document.file_id:
            new_id = msg.document.file_id
            log.info(f"PDF file_id capturado: {new_id}")
            # avisa no console e (se configurado) envia pra você
            if ADMIN_ID:
                try:
                    await context.bot.send_message(int(ADMIN_ID), f"✅ file_id do PDF capturado:\n{new_id}\n\nAdicione em FILE_ID no Railway para envios instantâneos.")
                except Exception as e:
                    log.warning(f"Falha ao avisar ADMIN: {e}")

    except Exception as e:
        log.error(f"Erro ao enviar PDF: {e}")
        await context.bot.send_message(chat_id, "⚠️ Não consegui enviar o PDF agora. Tenta /start de novo depois.")

# ================== SCHEDULER ==================
async def _schedule_unique(job_queue, name: str, when: time, chat_id: int, callback):
    for j in job_queue.get_jobs_by_name(name):
        j.schedule_removal()
    job_queue.run_daily(callback, when, chat_id=chat_id, name=name)

async def schedule_all_user_jobs(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    jq = context.job_queue
    await _schedule_unique(jq, f"pre_10_{chat_id}",   time(9, 30, tzinfo=TZ),  chat_id, pre10_cb)
    await _schedule_unique(jq, f"pre_15_{chat_id}",   time(14, 30, tzinfo=TZ), chat_id, pre15_cb)
    await _schedule_unique(jq, f"pre_20_{chat_id}",   time(19, 30, tzinfo=TZ), chat_id, pre20_cb)
    await _schedule_unique(jq, f"pos_10_{chat_id}",   time(10, 15, tzinfo=TZ), chat_id, pos10_cb)
    await _schedule_unique(jq, f"pos_15_{chat_id}",   time(15, 15, tzinfo=TZ), chat_id, pos15_cb)
    await _schedule_unique(jq, f"pos_20_{chat_id}",   time(20, 15, tzinfo=TZ), chat_id, pos20_cb)
    await _schedule_unique(jq, f"extra_1130_{chat_id}", time(11, 30, tzinfo=TZ), chat_id, extra1130_cb)
    await _schedule_unique(jq, f"extra_1630_{chat_id}", time(16, 30, tzinfo=TZ), chat_id, extra1630_cb)
    await _schedule_unique(jq, f"extra_1830_{chat_id}", time(18, 30, tzinfo=TZ), chat_id, extra1830_cb)
    await _schedule_unique(jq, f"boanoite_{chat_id}", time(22, 0, tzinfo=TZ),  chat_id, boanoite_cb)

async def unschedule_all_user_jobs(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    jq = context.job_queue
    for j in jq.jobs():
        if j.name.endswith(f"_{chat_id}"):
            j.schedule_removal()

# ================== JOB CALLBACKS ==================
async def pre10_cb(context):   await send_from_pool("pre10", context, context.job.chat_id, "10")
async def pre15_cb(context):   await send_from_pool("pre15", context, context.job.chat_id, "15")
async def pre20_cb(context):   await send_from_pool("pre20", context, context.job.chat_id, "20")
async def pos10_cb(context):   await send_from_pool("pos10", context, context.job.chat_id, "10")
async def pos15_cb(context):   await send_from_pool("pos15", context, context.job.chat_id, "15")
async def pos20_cb(context):   await send_from_pool("pos20", context, context.job.chat_id, "20")
async def extra1130_cb(context): await send_from_pool("extra1130", context, context.job.chat_id)
async def extra1630_cb(context): await send_from_pool("extra1630", context, context.job.chat_id)
async def extra1830_cb(context): await send_from_pool("extra1830", context, context.job.chat_id)
async def boanoite_cb(context):  await send_from_pool("boanoite", context, context.job.chat_id)

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("onboarded"):
        await update.message.reply_text("Você já está ativo. Quer ver as sessões do dia?", reply_markup=botoes_menu())
        return
    context.user_data["awaiting_name"] = True
    await update.message.reply_text("Opa, seja bem-vindo 😎 Me fala seu nome e já libero teu bônus!")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.user_data.get("awaiting_name"):
        nome = (update.message.text or "").strip()
        context.user_data["nome"] = nome
        context.user_data["awaiting_name"] = False

        await context.bot.send_message(chat_id, f"Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus exclusivo 👇")
        await send_bonus_pdf(context, chat_id)
        await context.bot.send_message(chat_id, "Atalhos rápidos pra começar agora 👇", reply_markup=botoes_menu())

        await schedule_all_user_jobs(context, chat_id)
        context.user_data["onboarded"] = True
        await context.bot.send_message(chat_id, "✅ Mensagens automáticas ativadas. Qualquer dúvida, fala comigo aqui.")
        return
    await update.message.reply_text("Escolhe uma opção 👇", reply_markup=botoes_menu())

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "sessoes":
        texto = "🕐 Sessões de Hoje\n• 10h\n• 15h\n• 20h"
        await q.edit_message_text(texto, reply_markup=botoes_menu())

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await unschedule_all_user_jobs(context, chat_id)
    await update.message.reply_text("⛔️ Mensagens automáticas desativadas pra você. Se quiser voltar, manda /start.")

# ================== MAIN ==================
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Defina BOT_TOKEN no ambiente (.env/variables).")
    persistence = PicklePersistence(filepath="state_oraculo_bot.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Bot iniciado. Aguardando mensagens…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
