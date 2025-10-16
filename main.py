import os
import random
import logging
from datetime import datetime, time, timedelta

import pytz
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------------------- LOGGING ----------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("oraculo-bonus-bot")

# ---------------------- VARIÁVEIS DE AMBIENTE ----------------------
BOT_TOKEN  = os.getenv("BOT_TOKEN")
LINK_CAD   = os.getenv("LINK_CAD")     # HomeBroker / cadastro
LINK_VIDEO = os.getenv("LINK_VIDEO")   # Vídeo explicativo
PDF_URL    = os.getenv("PDF_URL")      # Link direto do PDF
GROUP_LINK = os.getenv("GROUP_LINK", os.getenv("LINK_GROUP", ""))  # opcional; se faltar, omitimos o botão ABRIR

TZ = pytz.timezone("America/Sao_Paulo")

# ---------------------- ESTADO / MEMÓRIA ----------------------
ASK_NAME = 1
SUBSCRIBERS: set[int] = set()  # chat_ids que receberão as mensagens automáticas

# ---------------------- UTIL ----------------------
EMOJIS = ["💰","🔥","📈","⚡","🚀","📊","💎","😎","💥","🏆"]

def maybe_add_emoji(text: str) -> str:
    """60% de chance de acrescentar um emoji no FINAL da mensagem."""
    if random.random() < 0.6:
        return f"{text} {random.choice(EMOJIS)}"
    return text

def cta_keyboard() -> InlineKeyboardMarkup:
    """Alterna CTAs entre Começar Agora (HomeBroker) e ABRIR (Grupo)."""
    # Sempre teremos o Começar Agora; o ABRIR só se houver GROUP_LINK
    rows = []

    # linha 1: CTA principal (alternado)
    if random.random() < 0.5:
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])
        if GROUP_LINK:
            rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    else:
        if GROUP_LINK:
            rows.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
        rows.append([InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)])

    # linha 2: vídeo explicativo às vezes
    if LINK_VIDEO and random.random() < 0.4:
        rows.append([InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)])

    return InlineKeyboardMarkup(rows)

def fixed_shortcuts_keyboard() -> InlineKeyboardMarkup:
    """Atalhos fixos após o onboarding."""
    buttons = [
        [InlineKeyboardButton("🎥 Ver vídeo explicativo", url=LINK_VIDEO)] if LINK_VIDEO else [],
        [InlineKeyboardButton("🚀 Começar Agora", url=LINK_CAD)],
        [InlineKeyboardButton("⚡ Sessões do Dia", callback_data="sessoes")],
    ]
    if GROUP_LINK:
        buttons.append([InlineKeyboardButton("✅ ABRIR", url=GROUP_LINK)])
    # remove linhas vazias (caso não tenha LINK_VIDEO)
    buttons = [row for row in buttons if row]
    return InlineKeyboardMarkup(buttons)

def br_time(h: int, m: int =0) -> datetime:
    now = datetime.now(TZ)
    dt = TZ.localize(datetime(now.year, now.month, now.day, h, m, 0))
    return dt

def rand_minute(base_dt: datetime, minus: int, plus: int) -> datetime:
    """Desloca base_dt aleatoriamente em minutos dentro de [-minus, +plus]."""
    delta_min = random.randint(-minus, plus)
    return base_dt + timedelta(minutes=delta_min)

# ---------------------- MENSAGENS (30 por ocasião) ----------------------
PRE_MSGS = [
    "Se posiciona agora — estamos abrindo a sessão!",
    "Atenção: setup aquecendo para entradas certeiras.",
    "Foco total agora — ajuste a banca e vem junto.",
    "Preparado? Sinal na pista em instantes.",
    "Gestão em dia, emoção controlada. Partiu sessão.",
    "Quem chegou cedo, lucra primeiro. Bora!",
    "Hora de aquecer os motores da banca.",
    "Sem pressa, sem ansiedade: estratégia acima de tudo.",
    "Coloque sua plataforma no gatilho.",
    "Checklist feito? Vamos começar direito.",
    "Hoje a meta é simples: consistência.",
    "Evite distrações — 15 minutos de foco rendem o dia.",
    "Aproveite as melhores janelas. Vamos nessa.",
    "Separa sua meta e seu stop. Disciplina!",
    "Vem pra cima com calma e precisão.",
    "A sessão vai começar. Posiciona e respira.",
    "Nada de all-in — gestão vence o jogo.",
    "Os melhores pontos surgem para quem está pronto.",
    "Aproveite os sinais com responsabilidade.",
    "Bora rodar como time vencedor.",
    "Quem age primeiro, lucra primeiro.",
    "Seu futuro agradece a disciplina de agora.",
    "Hora de executar, sem inventar moda.",
    "Ajuste o volume e bora operar.",
    "Operação não é loteria, é método.",
    "Vem garantir o teu lugar na sessão.",
    "Partiu fazer o simples bem-feito.",
    "Resultados são consequência da execução.",
    "Atenção total: prepare-se para a primeira entrada.",
    "Relaxa, respira e foco no plano."
]

DURING_MSGS = [
    "Entrada identificada. Faça o básico e protege o caixa.",
    "Nada de afobação — siga o plano.",
    "Melhor ponto chegando… olhos na tela.",
    "Confirme a leitura antes de clicar.",
    "Metas pequenas, constância gigante.",
    "Protege o lucro e segue a gestão.",
    "Se não encaixar no plano, pula a operação.",
    "Mercado dá sinal todo dia; calma, sempre tem próximo.",
    "A entrada certa paga o dia.",
    "Confiança no método > impulso.",
    "Lembre que menos é mais.",
    "Você não precisa vencer todas, só ser consistente.",
    "Ajuste fino agora vale ouro.",
    "Sem FOMO — siga os sinais, não as emoções.",
    "Se moveu demais, espera a próxima oportunidade.",
    "Trabalha com o que o mercado te dá.",
    "A confirmação é sua melhor amiga.",
    "Segurança primeiro, sempre.",
    "Lembre da sua meta — não force operação.",
    "Entrou? Gestão apertada e sem teimosia.",
    "Nada de vingar trade — simplesmente segue.",
    "Oportunidade vista não significa obrigação de entrar.",
    "Cumpra sua regra, proteja seu caixa.",
    "Paciência paga mais do que pressa.",
    "A leitura confirma a decisão — não o contrário.",
    "Sinal bom aparece de novo. Calma.",
    "Quando o mercado acelera, você desacelera.",
    "Cada clique é uma decisão — faça valer.",
    "Entrada limpa > entrada rápida.",
    "Continue fazendo o simples."
]

POST_MSGS = [
    "Sessão encerrada. Anote seus resultados e revise 2 pontos de melhoria.",
    "Fechamos mais uma. Consistência acima de tudo.",
    "Resultado anotado? Gestão em dia, mente tranquila.",
    "Quem domina a gestão, domina o jogo.",
    "Pausa consciente agora evita erro depois.",
    "Parabéns por seguir o plano — isso vale mais que qualquer win.",
    "Fechamento feito. Não devolva lucro fora de hora.",
    "Revisão curtinha: 3 acertos, 1 ajuste e partiu próxima sessão.",
    "Stop dado? Aceita e segue o plano.",
    "Meta batida? Zera a plataforma e comemora com responsabilidade.",
    "Aprendizado anotado é lucro futuro.",
    "Sem revenge. Amanhã tem mercado de novo.",
    "A força está na disciplina diária.",
    "Você está construindo consistência. Continua.",
    "Nada de operar por tédio — fecha a tela.",
    "Controle > Ganância. Esse é o caminho.",
    "O que funcionou hoje? Repita. O resto, descarte.",
    "A paz de quem seguiu a gestão é impagável.",
    "Tamo junto. Próxima sessão te espera.",
    "Respira, hidrata e volta no horário certo.",
    "Resultado não define você; processo sim.",
    "Seja frio no win e no loss.",
    "Quem escreve, evolui mais rápido.",
    "Revisão final feita. Até a próxima!",
    "Seu eu do futuro te agradece pela disciplina.",
    "Foco no longo prazo: consistência diária.",
    "Ajuste pequeno hoje evita erro grande amanhã.",
    "Se motive pela execução, não pelo hype.",
    "Orgulho de quem fez o simples.",
    "Sessão concluída com responsabilidade."
]

GOOD_NIGHT_MSGS = [
    "Dia fechado. Durma bem e recarregue — amanhã tem mais.",
    "Boa noite! Consistência é construída no descanso também.",
    "Orgulhe-se do que construiu hoje. Até amanhã!",
    "Foco, fé e gestão. Amanhã seguimos.",
    "Descanse a mente para evoluir no próximo dia.",
    "Quem respeita o processo descansa sem culpa.",
    "Fechou por hoje. Gratidão e até a próxima.",
    "Cuidar do sono é parte da estratégia.",
    "Amanhã escrevemos mais uma página de consistência.",
    "Boa noite, time! Vocês estão no caminho certo.",
    "Você fez o que precisava hoje. Agora, descanso.",
    "Resultados gostam de mente descansada.",
    "Guerreiro descansa para voltar melhor.",
    "Paz na mente, gestão no bolso.",
    "Desliga as telas — amanhã a gente voa.",
    "Fechamento concluído. Até a próxima sessão!",
    "Tudo certo por hoje. Boa noite!",
    "A constância começa no hábito. Durma bem.",
    "Se cuide — disciplina também é saúde.",
    "Amanhã a gente repete o método. Boa noite!",
    "Quem é consistente sabe a hora de parar.",
    "Rotina vence motivação. Bom descanso!",
    "Nada de operar de madrugada. Durma :)",
    "Você está construindo o que sonha. Boa noite.",
    "Recarrega que o jogo é diário.",
    "Feito é melhor que perfeito. Até amanhã!",
    "Orgulho do time. Boa noite!",
    "Amanhã tem mais execução simples.",
    "Descanse com a consciência tranquila.",
    "Fechamos! Bons sonhos."
]

# ---------------------- HANDLERS ----------------------
WELCOME_TXT = "Opa, seja bem-vindo 😎 Me fala teu nome e já libero teu bônus!"
AFTER_NAME_TXT = "Shooow, {nome}! Parabéns por fazer parte do nosso time!\n\nAqui está seu bônus 👇"

SESSOES_TXT = (
    "⚡ Sessões do dia\n• 10:00\n• 15:00\n• 20:00\n\n"
    "🗓️ Cronograma semanal:\n• Segunda a Sexta: 10:00, 15:00, 20:00"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text(WELCOME_TXT)
    return ASK_NAME

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    name = update.message.text.strip()
    SUBSCRIBERS.add(update.effective_chat.id)

    # 1) Mensagem + PDF
    await update.message.reply_text(AFTER_NAME_TXT.format(nome=name))
    if PDF_URL:
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=PDF_URL,
                caption="📄 Guia Oráculo Black — seu material de início!"
            )
        except Exception as e:
            log.warning(f"Falha ao enviar PDF: {e}")

    # 2) Mensagem “CLIQUE AQUI...” + botão Começar Agora
    if LINK_CAD:
        txt = "**CLIQUE AQUI** para receber 10.000 e começar a operar agora mesmo:"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{txt}\n{LINK_CAD}",
            parse_mode=ParseMode.MARKDOWN
        )

    # 3) Atalhos rápidos (sem “Resgatar Bônus” no futuro)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Atalhos rápidos pra começar 👇",
        reply_markup=fixed_shortcuts_keyboard()
    )
    return ConversationHandler.END

async def sessoes_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(SESSOES_TXT)

# ---------------------- ENVIO AOS INSCRITOS ----------------------
async def broadcast(context: ContextTypes.DEFAULT_TYPE, pool: list[str], tag: str):
    """Envia 1 mensagem escolhida da pool + CTA aos inscritos."""
    if not SUBSCRIBERS:
        return
    text = maybe_add_emoji(random.choice(pool))
    for chat_id in list(SUBSCRIBERS):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=cta_keyboard())
        except Exception as e:
            log.warning(f"Falha ao enviar ({tag}) para {chat_id}: {e}")

# ---- Funções por fase (pré, durante com múltiplas msgs, pós, boa-noite)
async def send_pre_morning(context):  await broadcast(context, PRE_MSGS, "pre_morning")
async def send_pre_afternoon(context): await broadcast(context, PRE_MSGS, "pre_afternoon")
async def send_pre_night(context):     await broadcast(context, PRE_MSGS, "pre_night")

async def send_post_morning(context):  await broadcast(context, POST_MSGS, "post_morning")
async def send_post_afternoon(context):await broadcast(context, POST_MSGS, "post_afternoon")
async def send_post_night(context):    await broadcast(context, POST_MSGS, "post_night")

async def send_good_night(context):    await broadcast(context, GOOD_NIGHT_MSGS, "good_night")

async def send_during_burst(context: ContextTypes.DEFAULT_TYPE, tag: str):
    """Envia 2 a 3 mensagens durante a janela da sessão (20 min)."""
    n = random.randint(2, 3)
    for i in range(n):
        await broadcast(context, DURING_MSGS, f"during_{tag}")
        # espera entre 3 a 7 minutos entre mensagens
        await context.job_queue.run_once(lambda ctx: None, when=0)  # tick
        await context.application.create_task(_sleep_minutes(random.randint(3, 7)))

async def _sleep_minutes(m: int):
    await asyncio.sleep(m * 60)

# ---------------------- AGENDAMENTO ----------------------
import asyncio

def schedule_daily_jobs(app):
    jq = app.job_queue

    # Pré-sessões (aleatório próximo ao horário)
    jq.run_daily(send_pre_morning, rand_minute(br_time(9,50), 5, 5).timetz(), name="pre_morning", timezone=TZ)
    jq.run_daily(send_pre_afternoon, rand_minute(br_time(14,50), 5, 5).timetz(), name="pre_afternoon", timezone=TZ)
    jq.run_daily(send_pre_night, rand_minute(br_time(19,50), 5, 5).timetz(), name="pre_night", timezone=TZ)

    # Durante: agenda uma tarefa que dispara um burst entre 10:00–10:20, 15:00–15:20, 20:00–20:20
    async def morning_burst(ctx): await send_during_burst(ctx, "morning")
    async def afternoon_burst(ctx): await send_during_burst(ctx, "afternoon")
    async def night_burst(ctx): await send_during_burst(ctx, "night")

    # usamos run_daily para disparar no início da janela; os envios internos usam sleeps aleatórios
    jq.run_daily(morning_burst, br_time(10, 0).timetz(), name="during_morning", timezone=TZ)
    jq.run_daily(afternoon_burst, br_time(15, 0).timetz(), name="during_afternoon", timezone=TZ)
    jq.run_daily(night_burst, br_time(20, 0).timetz(), name="during_night", timezone=TZ)

    # Pós-sessões (com leve aleatorização)
    jq.run_daily(send_post_morning, rand_minute(br_time(10,40), 5, 5).timetz(), name="post_morning", timezone=TZ)
    jq.run_daily(send_post_afternoon, rand_minute(br_time(15,40), 5, 5).timetz(), name="post_afternoon", timezone=TZ)
    jq.run_daily(send_post_night, rand_minute(br_time(21,0), 5, 5).timetz(), name="post_night", timezone=TZ)

    # Boa noite fixa
    jq.run_daily(send_good_night, time(22,30,0, tzinfo=TZ), name="good_night", timezone=TZ)

# ---------------------- MAIN ----------------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não encontrado nas variáveis de ambiente.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(sessoes_btn, pattern="^sessoes$"))

    # agenda jobs diários
    schedule_daily_jobs(app)

    log.info("Bot iniciado. Agendadores ativos (BR -03:00).")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
