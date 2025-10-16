import os
import random
import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
    JobQueue,
)

# =========================
# LOG
# =========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("oraculo-bonus-bot")

# =========================
# AMBIENTE
# =========================
BOT_TOKEN  = os.getenv("BOT_TOKEN")
PDF_URL    = os.getenv("PDF_URL", "guia_oraculo_black.pdf")
LINK_CAD   = os.getenv("LINK_CAD", "https://bit.ly/COMECENOORACULOBLACK")
LINK_VIDEO = os.getenv("LINK_VIDEO", "https://t.me/oraculoblackfree")

if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente (.env/Railway).")

TZ = ZoneInfo("America/Sao_Paulo")

# =========================
# BOTÕES / CTA
# =========================
def keyboard_default(abrir_primeiro: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if abrir_primeiro:
        rows.append([InlineKeyboardButton("✅ ABRIR", url=LINK_VIDEO)])
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
    else:
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
        rows.append([InlineKeyboardButton("✅ ABRIR", url=LINK_VIDEO)])
    rows.insert(0, [InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])
    rows.append([InlineKeyboardButton("⚡ Sessões do Dia", callback_data="noop")])
    return InlineKeyboardMarkup(rows)

def _cta_keyboard_alterna() -> InlineKeyboardMarkup:
    return keyboard_default(abrir_primeiro=bool(random.getrandbits(1)))

# =========================
# CONSTRUÇÃO DE MENSAGENS
# (30 por ocasião asseguradas)
# =========================
EMOJIS_FIM = ["🔥","🚀","💥","⚡️","✅","📈","💰","🎯","🕒","🏁","📣","🧠","👊","🏆","🎉"]
SALDOS = ["saldo demo", "saldo de treino", "capital de teste"]
VERBOS = [
    "Bora pra cima", "Partiu executar", "Chegou tua hora", "Não fica de fora",
    "É agora", "Vem pro jogo", "Confirma tua entrada", "Aproveita a janela",
    "A hora é agora", "Só vem"
]

def _with_emojis_finais(txt: str, prob: float = 0.85, max_qtd: int = 2) -> str:
    if random.random() > prob:
        return txt
    qtd = random.randint(1, max_qtd)
    return txt.rstrip() + " " + " ".join(random.sample(EMOJIS_FIM, k=qtd))

def _craft_variations(frases: list[str], alvo: int = 30) -> list[str]:
    moldes = []
    for s in frases:
        moldes.append(_with_emojis_finais(s + " Bora!", 0.9))
        moldes.append(_with_emojis_finais(s + " Vem com a gente!", 0.85))
        moldes.append(_with_emojis_finais(s, 0.75))
    uniq = []
    for x in moldes:
        if x not in uniq:
            uniq.append(x)
        if len(uniq) >= alvo:
            break
    while len(uniq) < alvo:
        uniq.append(_with_emojis_finais(random.choice(frases) + " Agora!", 0.9))
    return uniq[:alvo]

def base_pos(hora_label: str) -> list[str]:
    h = hora_label
    b = [
        f"Já tem gente faturando na sessão das {h}! Você vai ficar de fora?",
        f"A sessão das {h} tá chamando. Entra e coloca teu {random.choice(SALDOS)} pra rodar!",
        f"{VERBOS[0]} na das {h}. Quem age primeiro, colhe primeiro!",
        f"Reta final pra sessão das {h}. Garanta tua posição!",
        f"Atenção: oportunidade aberta agora na das {h}.",
        f"A das {h} tá quente. Se posiciona e segue o plano!",
        f"Quem tá dentro da das {h} tá avançando. Vem junto!",
        f"Sem enrolação: {h} é a hora. Faz teu movimento!",
        f"Quer resultado? Cola na das {h} e executa sem medo.",
        f"{VERBOS[1]} na das {h}. Sem desculpa!",
        f"Convite direto: sessão {h}. Tua virada começa na ação!",
        f"Aproveita a onda da sessão {h}. Ajusta teu {random.choice(SALDOS)} e vai!",
        f"{VERBOS[2]}: {h}. É simples: entrar e executar.",
        f"Se decidir agora, você entra na das {h}. Não posterga!",
        f"A vitrine tá aberta na {h}. Quem decide, participa!",
        f"Confirma tua entrada na sessão {h}. Foco e execução!",
        f"Quem procrastina perde a das {h}. Decide e entra!",
        f"Se quer consistência, aparece na das {h} e aplica o básico!",
        f"A sessão {h} é tua porta de entrada hoje. Passa e executa!",
        f"Resultado não cai do céu. Entra na {h} e faz acontecer!",
    ]
    return _craft_variations(b, 30)

def base_extra(tag: str) -> list[str]:
    b = [
        f"Extra {tag} no ar! Pega a deixa e executa.",
        f"Rolando agora: Extra {tag}. Aproveita a janela.",
        f"Chamado rápido: Extra {tag}. Ajusta teu {random.choice(SALDOS)} e vai.",
        f"Extra {tag} fervendo. Quem entra, aproveita.",
        f"Movimento acontecendo na Extra {tag}. Bora pro jogo!",
        f"Extra {tag} aberta. Oportunidade não espera!",
        f"Quem entrou na Extra {tag} já tá vendo resultado. Não deixa passar.",
        f"Se perdeu o horário principal, a Extra {tag} tá aí. Entra agora!",
        f"A Extra {tag} é pra quem não gosta de perder tempo. Vai!",
        f"Agora é a tua. Extra {tag} liberada.",
        f"Chamada rápida: Extra {tag}. Vem garantir teu espaço.",
        f"Executa o plano na Extra {tag}. Simples e direto.",
        f"Extra {tag} aquecida. Posiciona e confirma.",
        f"Não marca bobeira: Extra {tag} acontecendo agora.",
        f"Extra {tag} com fluxo rolando. Aproveita!",
        f"Perdeu o início? Recupera na Extra {tag}.",
        f"Extra {tag}: chance clara pra acelerar aprendizado.",
        f"Quem busca ritmo, entra na Extra {tag} e executa.",
        f"Extra {tag} aberta — faz a tua parte!",
        f"Oportunidade bônus: Extra {tag}.",
    ]
    return _craft_variations(b, 30)

def base_boanoite() -> list[str]:
    b = [
        "Boa noite! Fechamos o dia e amanhã te espero com a gente.",
        "Fechamos o dia por aqui. Amanhã tem mais — cola com a gente!",
        "Boa noite! Amanhã seguimos firmes nas sessões.",
        "Encerramos por hoje. Descansa que amanhã tem jogo de novo.",
        "Fechou! Amanhã tem sessão 10h/15h/20h. Te aguardo.",
        "Fim de dia por aqui. Amanhã é mais um passo no plano.",
        "Boa noite! Amanhã você entra pra executar com foco.",
        "Por hoje é isso. Amanhã a gente acelera junto.",
        "Fechou o dia! Amanhã segue o baile com as sessões.",
        "Boa! Amanhã tem mais oportunidades — te espero.",
        "Encerrado por hoje. Amanhã você entra preparado!",
        "Boa noite! Amanhã conecta e executa com a gente.",
        "Dia encerrado. Amanhã é dia de ação de novo.",
        "Valeu por hoje! Amanhã cola nas sessões.",
        "Boa noite — foco, descanso e amanhã a gente volta.",
        "Missão cumprida hoje. Amanhã seguimos no plano.",
        "Gratidão por hoje. Amanhã você entra mais afiado.",
        "Fecha o dia com tranquilidade. Amanhã é execução.",
        "Boa noite! Amanhã é mais um passo pra frente.",
        "Descansa. Amanhã a gente te espera às 10h/15h/20h.",
    ]
    return _craft_variations(b, 30)

# pools (30 mensagens garantidas cada)
POOL_MAP = {
    "pos10":     base_pos("10h"),
    "pos15":     base_pos("15h"),
    "pos20":     base_pos("20h"),
    "extra1130": base_extra("11:30"),
    "extra1630": base_extra("16:30"),
    "extra1830": base_extra("18:30"),
    "boanoite":  base_boanoite(),
}

# =========================
# SUBSCRIÇÃO (quem deu /start)
# =========================
SUBS_KEY = "subscribers"

def add_subscriber(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    data = context.application.bot_data
    subs = data.get(SUBS_KEY, set())
    subs.add(chat_id)
    data[SUBS_KEY] = subs

def get_subscribers(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get(SUBS_KEY, set())

# =========================
# ENVIO DE UMA MENSAGEM DE POOL
# =========================
async def send_from_pool(pool: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        msgs = POOL_MAP.get(pool, [])
        if not msgs:
            await context.bot.send_message(chat_id, f"⚠️ Pool vazio: {pool}")
            return
        texto = random.choice(msgs)
        await context.bot.send_message(chat_id=chat_id, text=texto, reply_markup=_cta_keyboard_alterna())
    except Exception as e:
        log.exception(f"[send_from_pool] {pool}: {e}")
        await context.bot.send_message(chat_id, f"⚠️ Erro ao enviar [{pool}]: {e}")

# =========================
# PDF
# =========================
async def send_bonus_pdf(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        base = "/app" if os.path.exists("/app") else "."
        pdf_path = os.path.join(base, PDF_URL)
        if os.path.exists(pdf_path):
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(pdf_path, "rb"),
                caption="📘 Guia Oráculo Black — o seu bônus de início!",
            )
        else:
            await context.bot.send_message(chat_id, "⚠️ Não achei o PDF no servidor.")
    except Exception as e:
        log.exception(f"[PDF] {e}")
        await context.bot.send_message(chat_id, f"⚠️ Falha ao enviar PDF: {e}")

# =========================
# COMANDOS
# =========================
async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    await u.message.reply_text("Opa, seja bem-vindo 😎 Me fala seu nome e já libero teu bônus!")
    try:
        nome = (await c.bot.get_chat(chat_id)).first_name or "Trader"
    except:
        nome = "Trader"
    await c.bot.send_message(chat_id, f"Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇")
    await send_bonus_pdf(c, chat_id)
    await c.bot.send_message(chat_id, "Atalhos rápidos pra começar 👇", reply_markup=keyboard_default())
    add_subscriber(c, chat_id)

async def cmd_help(u: Update, c: ContextTypes.DEFAULT_TYPE):
    comandos = (
        "/start /help /sessoes /pdf /teste\n"
        "/poolpos10 /poolpos15 /poolpos20\n"
        "/poolextra1130 /poolextra1630 /poolextra1830 /poolboanoite"
    )
    await u.message.reply_text(f"Comandos:\n{comandos}")

async def cmd_pdf(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await send_bonus_pdf(c, u.effective_chat.id)

async def cmd_sessoes(u: Update, c: ContextTypes.DEFAULT_TYPE):
    texto = (
        "⚡ Sessões do dia\n"
        "• 10:00\n• 15:00\n• 20:00\n\n"
        "🗓 Cronograma semanal:\n"
        "• Segunda-feira: 10:00, 15:00, 20:00\n"
        "• Terça-feira: 10:00, 15:00, 20:00\n"
        "• Quarta-feira: 10:00, 15:00, 20:00\n"
        "• Quinta-feira: 10:00, 15:00, 20:00\n"
        "• Sexta-feira: 10:00, 15:00, 20:00\n"
        "• Sábado: 10:00, 15:00, 20:00\n"
        "• Domingo: 10:00, 15:00, 20:00"
    )
    await u.message.reply_text(texto)

async def cmd_teste(u: Update, c: ContextTypes.DEFAULT_TYPE):
    chat_id = u.effective_chat.id
    try:
        await send_from_pool("pos10", c, chat_id)
        await send_from_pool("pos15", c, chat_id)
        await send_from_pool("extra1130", c, chat_id)
        await send_from_pool("boanoite", c, chat_id)
        await u.message.reply_text("✅ Testes enviados.")
    except Exception as e:
        log.exception(f"[TESTE] {e}")
        await u.message.reply_text(f"⚠️ Falhou: {e}")

async def cmd_poolpos10(u,c):     await send_from_pool("pos10", c, u.effective_chat.id)
async def cmd_poolpos15(u,c):     await send_from_pool("pos15", c, u.effective_chat.id)
async def cmd_poolpos20(u,c):     await send_from_pool("pos20", c, u.effective_chat.id)
async def cmd_poolextra1130(u,c): await send_from_pool("extra1130", c, u.effective_chat.id)
async def cmd_poolextra1630(u,c): await send_from_pool("extra1630", c, u.effective_chat.id)
async def cmd_poolextra1830(u,c): await send_from_pool("extra1830", c, u.effective_chat.id)
async def cmd_poolboanoite(u,c):  await send_from_pool("boanoite", c, u.effective_chat.id)

# =========================
# BROADCAST / AGENDAS
# =========================
async def _broadcast_pool(context: ContextTypes.DEFAULT_TYPE, pool: str):
    subs = list(get_subscribers(context))
    if not subs:
        return
    for chat_id in subs:
        await send_from_pool(pool, context, chat_id)

def schedule_jobs(app):
    # Inicializa JobQueue manualmente (necessário no Railway)
    if not hasattr(app, "job_queue") or app.job_queue is None:
        app.job_queue = JobQueue()
        app.job_queue.set_application(app)
        app.job_queue.start()
        log.info("✅ JobQueue inicializado manualmente.")

    jq = app.job_queue
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos10"),     time=time(10,15, tzinfo=TZ))  # Pós 10h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos15"),     time=time(15,15, tzinfo=TZ))  # Pós 15h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos20"),     time=time(20,15, tzinfo=TZ))  # Pós 20h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1130"), time=time(11,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1630"), time=time(16,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1830"), time=time(18,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "boanoite"),  time=time(22,00, tzinfo=TZ))
    log.info("⏰ Agendamentos diários configurados.")

# =========================
# MAIN
# =========================
def main():
    persistence = PicklePersistence(filepath="state_oraculo_bot.pickle")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()

    # comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("sessoes", cmd_sessoes))
    app.add_handler(CommandHandler("pdf",   cmd_pdf))
    app.add_handler(CommandHandler("teste", cmd_teste))
    app.add_handler(CommandHandler("poolpos10",      cmd_poolpos10))
    app.add_handler(CommandHandler("poolpos15",      cmd_poolpos15))
    app.add_handler(CommandHandler("poolpos20",      cmd_poolpos20))
    app.add_handler(CommandHandler("poolextra1130",  cmd_poolextra1130))
    app.add_handler(CommandHandler("poolextra1630",  cmd_poolextra1630))
    app.add_handler(CommandHandler("poolextra1830",  cmd_poolextra1830))
    app.add_handler(CommandHandler("poolboanoite",   cmd_poolboanoite))

    # agenda antes do polling
    schedule_jobs(app)

    log.info("🤖 Bot iniciado e agendado.")
    app.run_polling()

if __name__ == "__main__":
    main()
