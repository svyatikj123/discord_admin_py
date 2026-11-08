import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import os

# Замените на переменную окружения или вставьте свой новый токен
token = os.getenv('MTQ3NTA4MDExNzA2NjY2NTk5Ng.G1UG-P.-dzNxzaGxLp2V5FSYu6Qc8jUvywhXnMqbTQYvM') or 'MTQ3NTA4MDExNzA2NjY2NTk5Ng.G1UG-P.-dzNxzaGxLp2V5FSYu6Qc8jUvywhXnMqbTQYvM'

prefix = '/'
intents = discord.Intents().all()
bot = commands.Bot(command_prefix=prefix, intents=intents)

# Настройки yt-dlp для извлечения аудио
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # IPv4
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # Если это плейлист или поиск, берём первый результат
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Очередь для каждой гильдии
queues = {}

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue:
        return
    url = queue.pop(0)
    try:
        source = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'🎶 Сейчас играет: **{source.title}**')
    except Exception as e:
        await ctx.send(f'❌ Ошибка воспроизведения: {e}')
        await play_next(ctx)

@bot.command(name='join')
async def join(ctx):
    """Подключает бота к вашему голосовому каналу."""
    if not ctx.author.voice:
        return await ctx.send('Вы не находитесь в голосовом канале.')
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
        await ctx.send(f'✅ Подключился к каналу **{channel.name}**')
    else:
        await ctx.voice_client.move_to(channel)
        await ctx.send(f'✅ Переместился в канал **{channel.name}**')

@bot.command(name='play')
async def play(ctx, *, query: str):
    """Добавляет трек в очередь и начинает воспроизведение.
    Можно указать URL (YouTube, SoundCloud и т.д.) или поисковый запрос."""
    if not ctx.voice_client:
        await ctx.invoke(join)
    if not ctx.voice_client:
        return

    # Если это не URL, используем поиск YouTube
    if not query.startswith('http'):
        query = f'ytsearch:{query}'

    queue = get_queue(ctx.guild.id)
    queue.append(query)
    await ctx.send(f'➕ Добавлено в очередь: `{query}`')

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(name='pause')
async def pause(ctx):
    """Приостанавливает воспроизведение."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('⏸️ Пауза')
    else:
        await ctx.send('Сейчас ничего не играет.')

@bot.command(name='resume')
async def resume(ctx):
    """Возобновляет воспроизведение."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('▶️ Продолжаю')
    else:
        await ctx.send('Воспроизведение не приостановлено.')

@bot.command(name='skip')
async def skip(ctx):
    """Пропускает текущий трек."""
    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        ctx.voice_client.stop()
        await ctx.send('⏭️ Пропущено')
    else:
        await ctx.send('Нечего пропускать.')

@bot.command(name='stop')
async def stop(ctx):
    """Останавливает воспроизведение и очищает очередь."""
    if ctx.voice_client:
        queue = get_queue(ctx.guild.id)
        queue.clear()
        ctx.voice_client.stop()
        await ctx.send('⏹️ Остановлено, очередь очищена.')

@bot.command(name='leave')
async def leave(ctx):
    """Отключает бота от голосового канала."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)
        await ctx.send('👋 Отключился.')
    else:
        await ctx.send('Бот не в голосовом канале.')

@bot.command(name='queue')
async def queue_(ctx):
    """Показывает текущую очередь треков."""
    queue = get_queue(ctx.guild.id)
    if not queue:
        return await ctx.send('Очередь пуста.')
    msg = '\n'.join(f'{i+1}. {url}' for i, url in enumerate(queue))
    await ctx.send(f'**Очередь:**\n{msg}')

# --- Ваши существующие команды (оставлены без изменений) ---
@bot.command()
async def ser(ctx):
    for i in range(10):
        await ctx.reply("1")

async def mute_member(channels, member, mute):
    for channel in channels:
        for voice_member in channel.members:
            if member == voice_member:
                await member.edit(mute=mute)
                return

@bot.command('unmute')
async def mute(ctx, member: discord.Member = None):
    if member:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        await member.remove_roles(muted_role)
        await member.send(f"You have been unmuted")
        await mute_member(ctx.guild.voice_channels, member, False)
    else:
        await ctx.send("Didn't work, try using the command *properly*")

@bot.command('mute')
async def mute(ctx, member: discord.Member):
    await member.edit(mute=True)

@bot.command('muteall')
async def muteall(ctx):
    for channel in ctx.guild.voice_channels:
        for member in channel.members:
            await member.edit(mute=True)

@bot.command('unmuteall')
async def unmuteall(ctx):
    for channel in ctx.guild.voice_channels:
        for member in channel.members:
            await member.edit(mute=False)

@bot.command("uskick")
async def uskick(ctx, member: discord.Member):
    await member.edit(voice_channel=None)

@bot.command("usakick")
async def uskick(ctx):
    for channel in ctx.guild.voice_channels:
        for member in channel.members:
            await member.edit(voice_channel=None)

@bot.command("allmuteserv")
async def мут(ctx, member: discord.Member = None, amout: str = None, *, reason = None):
    await member.edit(mute=True)

# Запуск бота
bot.run(token)