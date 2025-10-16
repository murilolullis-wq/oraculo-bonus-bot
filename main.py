import os
import json
import random
import logging
from datetime import time, datetime
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

# =========================================
# LOG
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("oraculo-bonus-bot")

# =========================================
# AMBIENTE
# =========================================
BOT_TOKEN  = os.getenv("BOT_TOKEN")
PDF_URL    = os.getenv("PDF_URL", "guia_oraculo_black.pdf")
LINK_CAD   = os.getenv("LINK_CAD", "https://bit.ly/COMECENOORACULOBLACK")
LINK_VIDEO = os.getenv("LINK_VIDEO", "https://t.me/oraculoblackfree")

if not BOT_TOKEN:
    raise RuntimeError("Defina BOT_TOKEN no ambiente (.env / Railway).")

TZ = ZoneInfo("America/Sao_Paulo")  # agenda no fuso BR

# =========================================
# TECLADOS / CTAs
# =========================================
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

# =========================================
# SISTEMA DE MENSAGENS (30 por pool)
# =========================================
EMOJIS_FIM = ["🔥", "🚀", "💥", "⚡️", "✅", "📈", "💰", "🎯", "🕒", "🏁", "📣", "🧠", "👊", "🏆", "🎉"]
SALDOS = ["saldo demo", "saldo de treino", "capital de teste"]
CTA_VERBOS = [
    "Bora pra cima", "Partiu executar", "Chegou tua hora",
    "Não fica de fora", "É agora", "Vem pro jogo",
    "Confirma tua entrada", "Aproveita a janela",
    "A hora é agora", "Só vem"
]

def _mix_emojis(texto: str, chance: float = 0.85, max_qtd: int = 2) -> str:
    """Adiciona 0-2 emojis no fim (sem poluir o corpo)."""
    if random.random() > chance:
        return texto
    qtd = random.randint(1, max_qtd)
    escolhidos = random.sample(EMOJIS_FIM, k=qtd)
    return texto.rstrip() + " " + " ".join(escolhidos)

def _var_base(hora: str) -> list[str]:
    """Frases-base (agressivas/CTA), focadas na hora informada."""
    return [
        f"Já tem gente faturando na sessão das {hora}! Você vai ficar de fora?",
        f"A sessão das {hora} tá chamando. Entra e coloca teu {random.choice(SALDOS)} pra rodar!",
        f"{CTA_VERBOS[0]} na das {hora}. Quem age primeiro, colhe primeiro!",
        f"Reta final pra sessão das {hora}. Garanta tua posição!",
        f"Atenção: oportunidade aberta agora na das {hora}.",
        f"A das {hora} tá quente. Se posiciona e segue o plano!",
        f"Quem tá dentro da das {hora} tá avançando. Vem junto!",
        f"Sem enrolação: {hora} é a hora. Faz teu movimento!",
        f"Quer resultado? Cola na das {hora} e executa sem medo.",
        f"{CTA_VERBOS[1]} na das {hora}. Sem desculpa!",
        f"Convite direto: sessão {hora}. Tua virada começa na ação!",
        f"Aproveita a onda da sessão {hora}. Ajusta teu {random.choice(SALDOS)} e vai!",
        f"{CTA_VERBOS[2]}: {hora}. É simples: entrar e executar.",
        f"Se decidir agora, você entra na das {hora}. Não posterga!",
        f"A vitrine tá aberta na {hora}. Quem decide, participa!",
    ]

def _var_extra(tag: str) -> list[str]:
    """Frases-base para extras (11:30, 16:30, 18:30)."""
    return [
        f"Extra {tag} no ar! Pega a deixa e executa.",
        f"Rolando agora: Extra {tag}. Aproveita a janela.",
        f"Chamado rápido: Extra {tag}. Ajusta teu {random.choice(SALDOS)} e vai.",
        f"Extra {tag} fervendo. Quem entra, aproveita.",
        f"Movimento acontecendo na Extra {tag}. Bora pro jogo!",
        f"Extra {tag} aberta. Oportunidade não espera!",
        f"Quem entrou na Extra {tag} já tá vendo resultado. Não fica pra depois.",
        f"Se perdeu o horário principal, a Extra {tag} tá aí. Entra agora!",
        f"A Extra {tag} é pra quem não gosta de perder tempo. Vai!",
        f"Agora é a tua. Extra {tag} liberada.",
        f"Chamada rápida: Extra {tag}. Vem garantir teu espaço.",
        f"Executa o plano na Extra {tag}. Simples e direto.",
        f"Extra {tag} aquecida. Posiciona e confirma.",
        f"Não marca bobeira: Extra {tag} acontecendo agora.",
        f"Extra {tag} com fluxo rolando. Aproveita!",
    ]

def _var_noite() -> list[str]:
    return [
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
    ]

def gerar_pool_pos(hora: str) -> list[str]:
    base = _var_base(hora)
    extras = [
        f"Tá esperando o quê pra começar na sessão das {hora}? Decide e vai.",
        f"Quer resultado real? Entra na das {hora} e aplica o básico bem feito.",
        f"Sem desculpas: {hora}. Faz teu primeiro passo agora.",
        f"Se compromete com a sessão {hora} e executa até o final.",
        f"Você pediu direção. Tá aqui: sessão {hora}.",
    ]
    frases = base + extras
    # expande para 30 com variações + emojis ao fim
    moldes = []
    for s in frases:
        s1 = _mix_emojis(s + " Bora!", 0.9)
        s2 = _mix_emojis(s + " Vem com a gente!", 0.8)
        s3 = _mix_emojis(s, 0.7)
        moldes += [s1, s2, s3]
    # garante 30 distintas
    uniq = []
    for x in moldes:
        if x not in uniq:
            uniq.append(x)
        if len(uniq) >= 30:
            break
    return uniq[:30]

def gerar_pool_extra(tag: str) -> list[str]:
    base = _var_extra(tag)
    frases = base + [
        f"Extra {tag}: hora perfeita pra quem quer acelerar.",
        f"Extra {tag} aberta. Quem entra, executa.",
        f"Extra {tag} em andamento — posiciona e segue.",
    ]
    moldes = []
    for s in frases:
        moldes += [
            _mix_emojis(s + " Bora!", 0.9),
            _mix_emojis(s + " Cola agora!", 0.85),
            _mix_emojis(s, 0.7),
        ]
    uniq = []
    for x in moldes:
        if x not in uniq:
            uniq.append(x)
        if len(uniq) >= 30:
            break
    return uniq[:30]

def gerar_pool_noite() -> list[str]:
    base = _var_noite()
    moldes = []
    for s in base:
        moldes += [
            _mix_emojis(s, 0.7),
            _mix_emojis(s + " Até amanhã!", 0.8),
            _mix_emojis(s + " Bora descansar e voltar focado!", 0.85),
        ]
    uniq = []
    for x in moldes:
        if x not in uniq:
            uniq.append(x)
        if len(uniq) >= 30:
            break
    # se não atingiu 30, repete com leves variações
    while len(uniq) < 30:
        uniq.append(_mix_emojis(random.choice(base) + " Amanhã seguimos!", 0.85))
    return uniq[:30]

# pools pré-gerados (30 por pool)
POOL_MAP = {
    "pos10":     gerar_pool_pos("10h"),
    "pos15":     gerar_pool_pos("15h"),
    "pos20":     gerar_pool_pos("20h"),
    "extra1130": gerar_pool_extra("11:30"),
    "extra1630": gerar_pool_extra("16:30"),
    "extra1830": gerar_pool_extra("18:30"),
    "boanoite":  gerar_pool_noite(),
}

# =========================================
# SUBSCRIÇÃO (automaticamente quem deu /start)
# =========================================
SUBS_KEY = "subscribers"  # usado na persistência

def add_subscriber(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    data = context.application.bot_data
    subs = data.get(SUBS_KEY, set())
    subs.add(chat_id)
    data[SUBS_KEY] = subs

def get_subscribers(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get(SUBS_KEY, set())

# =========================================
# ENVIO DE MENSAGEM DE UM POOL
# =========================================
def _cta_keyboard_alterna() -> InlineKeyboardMarkup:
    return keyboard_default(abrir_primeiro=bool(random.getrandbits(1)))

async def send_from_pool(pool: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        msgs = POOL_MAP.get(pool, [])
        if not msgs:
            await context.bot.send_message(chat_id, f"⚠️ Pool vazio: {pool}")
            return
        texto = random.choice(msgs)
        await context.bot.send_message(chat_id=chat_id, text=texto, reply_markup=_cta_keyboard_alterna())
    except Exception as e:
        log.exception(f"[send_from_pool] {pool} -> erro: {e}")
        await context.bot.send_message(chat_id, f"⚠️ Erro ao enviar [{pool}]: {e}")

# =========================================
# PDF
# =========================================
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
        log.exception(f"[PDF] erro: {e}")
        await context.bot.send_message(chat_id, f"⚠️ Falha ao enviar PDF: {e}")

# =========================================
# COMANDOS
# =========================================
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
    comandos = "/start /help /sessoes /pdf /teste\n" \
               "/poolpos10 /poolpos15 /poolpos20\n" \
               "/poolextra1130 /poolextra1630 /poolextra1830 /poolboanoite"
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

# Pools (manuais)
async def cmd_poolpos10(u,c):     await send_from_pool("pos10", c, u.effective_chat.id)
async def cmd_poolpos15(u,c):     await send_from_pool("pos15", c, u.effective_chat.id)
async def cmd_poolpos20(u,c):     await send_from_pool("pos20", c, u.effective_chat.id)
async def cmd_poolextra1130(u,c): await send_from_pool("extra1130", c, u.effective_chat.id)
async def cmd_poolextra1630(u,c): await send_from_pool("extra1630", c, u.effective_chat.id)
async def cmd_poolextra1830(u,c): await send_from_pool("extra1830", c, u.effective_chat.id)
async def cmd_poolboanoite(u,c):  await send_from_pool("boanoite", c, u.effective_chat.id)

# =========================================
# AGENDAMENTO AUTOMÁTICO (envia pra todos que deram /start)
# =========================================
async def _broadcast_pool(context: ContextTypes.DEFAULT_TYPE, pool: str):
    subs = list(get_subscribers(context))
    if not subs:
        return
    for chat_id in subs:
        await send_from_pool(pool, context, chat_id)

def schedule_jobs(app):
    jq = app.job_queue
    # Horários no fuso BR
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos10"),     time=time(10,15, tzinfo=TZ))   # Pós 10h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos15"),     time=time(15,15, tzinfo=TZ))   # Pós 15h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "pos20"),     time=time(20,15, tzinfo=TZ))   # Pós 20h
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1130"), time=time(11,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1630"), time=time(16,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "extra1830"), time=time(18,30, tzinfo=TZ))
    jq.run_daily(lambda ctx: _broadcast_pool(ctx, "boanoite"),  time=time(22,00, tzinfo=TZ))
    log.info("⏰ Agendamentos diários configurados.")

# =========================================
# MAIN
# =========================================
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

    # pós init agenda
    async def _post_init(_):
        schedule_jobs(app)
        log.info("🤖 Bot pronto e agendado.")
    app.post_init = _post_init

    app.run_polling()

if __name__ == "__main__":
    main()
