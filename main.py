import wavelink
import discord
import json
from discord.ext import commands
from typing import cast


token = ""
channelID = 1200891188715208754
intents = discord.Intents.all()
Prefix = "!"

bot = commands.Bot(command_prefix=Prefix, intents=intents)

@bot.event
async def on_ready():
    print("Bot ready")
    LoadSettings()
    bot.loop.create_task(node_connect())
    
def LoadSettings():
    with open('archivo.json', 'r') as file:
        #Carga el contenido del archivo en un diccionario
        data = json.load(file)
    print(data)
    global channelID
    channelID = data["ChannelID"]
    global Prefix
    Prefix = data["Prefix"]
    bot.command_prefix = data["Prefix"]
    return

def SaveSettings():
    data_to_write = {
    "ChannelID": channelID,
    "Prefix": Prefix
    }
    
    with open('archivo.json', 'w') as file:
        #Escribe los datos en el archivo JSON
        json.dump(data_to_write, file, indent=2)
    return

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"Node is ready!")
    channel = bot.get_channel(channelID)
    await channel.send("Music Bot is Online")

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed: discord.Embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        channel = bot.get_channel(channelID)
        await channel.send(embed=embed)

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    return


async def node_connect():
    await bot.wait_until_ready()
    nodes = [wavelink.Node(uri="http://localhost:2333",password="youshallnotpass")]
    await wavelink.Pool.connect(nodes=nodes,client=bot,cache_capacity=None)


#Commands
@bot.command()
async def hello(ctx):
    await ctx.send("Hello")

#Setup
@bot.command(name="Setup", aliases=["setup", "Set","SU","su"])
async def setup(ctx):
    global channelID
    channelID = ctx.message.channel.id
    #Missing data persistence
    SaveSettings()
    await ctx.send("Bot setup configured")    

#Prefix
@bot.command(name="Prefix", aliases=["prefix","Pre","pre"])
async def prefix(ctx:commands.context,*,newprefix:str):
    bot.command_prefix = newprefix
    #Missing data persistence
    SaveSettings()
    await ctx.send(f"Command prefix changed to {newprefix}")
    

@bot.command()
async def test(ctx):
    channel = bot.get_channel(channelID)
    await channel.send(test) 


#Play    
@bot.command(name="Play", aliases=["play","p","P"],help="Plays a song or adds it to the queue. You can specify a search query or provide a direct link to the song.",brief="Play a song or add it to the queue.", category="Music", arguments="Query")
async def play(ctx: commands.Context, *, search: str):
    
    #Check for user in voice channel
    if not ctx.guild:
        return

    player: wavelink.Player
    player = cast(wavelink.Player, ctx.voice_client)

    if not player:
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except AttributeError:
            await ctx.send("Please join a voice channel first before using this command.")
            return
        except discord.ClientException:
            await ctx.send("I was unable to join this voice channel. Please try again.")
            return
    
    
    if not hasattr(player, "home"):
        player.home = ctx.channel
    elif player.home != ctx.channel:
        await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
        return
    
    #Eneable autoplay withour recomendations
    player.autoplay = wavelink.AutoPlayMode.partial
    
    #Search track 
    tracks: wavelink.Search = await wavelink.Playable.search(search)    
    if not tracks:
        await ctx.send(f"{ctx.author.mention} - Could not find any tracks. Please try again.")
        return
    
    #Add track to queue if already playing
    if isinstance(tracks, wavelink.Playlist):
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        await ctx.send(f"Added **`{track}`** to the queue.")
    
    #If not playing anything start playingt track
    if not player.playing:
        await player.play(player.queue.get(), volume=30)
    
#Skip   
@bot.command(name="Skip", aliases=["skip","s","S"], help="Skips the current song and plays the next one in the queue.",brief="Skip the current song.")
async def skip(ctx):
    #Skip the current song.
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await player.skip(force=True)
    await ctx.message.add_reaction("\u2705")

#Pause/Resume    
@bot.command(name="Toggle Pause", aliases=["pause", "resume","Pause","Resume","R"], help="Toggles pausing and resuming the current song playback.", brief="Toggle pause and resume playback.")
async def pause_resume(ctx: commands.Context) -> None:
    #Pause or Resume the Player depending on its current state.
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await player.pause(not player.paused)
    await ctx.message.add_reaction("\u2705")

#Disconnnect
@bot.command(name="Disconnect",aliases=["dc","DC","stop","Stop"], help="Disconnects the bot from the voice channel.", brief="Disconnects the bot from the voice channel.")
async def disconnect(ctx: commands.Context) -> None:
    #Disconnect the Player.
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return

    await player.disconnect()
    await ctx.message.add_reaction("\u2705")
 
#Shuffle
@bot.command(name="Shuffle", aliases=["shuffle","sh","SH"], help="Shuffles the order of songs in the queue.", brief="Shuffle the song queue.")
async def shuffle(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.queue.shuffle()
    await ctx.send("Playlist shuffled")
    
#Clear
@bot.command(name="Clear", aliases=["clear","c","C"], help="Clear the entire song queue.", brief="Clear the song queue.")
async def clear(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    await player.queue.clear()
    await ctx.send("Playlist cleared")

#ForcePlay
@bot.command(name="ForcePlay",aliases=["forceplay","FP","fp"], help="Queues the song to be the next one to play.", brief="Plays the song right after the current one.")
async def forceplay(ctx,*,search):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    tempQueue = list(player.queue)
    
    player.queue.clear()
    
     #Search track 
    tracks: wavelink.Search = await wavelink.Playable.search(search)    
    if not tracks:
        await ctx.send(f"{ctx.author.mention} - Could not find any tracks. Please try again.")
        return
    
    #Add track to queue if already playing
    if isinstance(tracks, wavelink.Playlist):
        added: int = await player.queue.put_wait(tracks)
        await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
    else:
        track: wavelink.Playable = tracks[0]
        await player.queue.put_wait(track)
        await ctx.send(f"Added **`{track}`** to the queue.")
     
    for item in tempQueue:    
        await player.queue.put_wait(item)

#Queue
@bot.command(name="Queue",aliases=["queue","Q","q"],help="Displays the current song queue.",brief="Show the current song queue.")
async def queue(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    #improve visual representation
    embed = discord.Embed(title='Song Queue', color=discord.Color.blue())

    for index, track in enumerate(player.queue, start=1):
        if(index>10):
            break
        embed.add_field(name=f'{index}. {track.title}', value=f'', inline=False)
#Requested by: {bot.get_user(track.requester).mention}
    print("sended queue")
    await ctx.send(embed=embed)
 
 #Loop
@bot.command(name="LoopSong", aliases=["loopsong","ls","LS"], help="Toggles looping of the current song. When enabled, the current song will repeat.",brief="Toggle looping of the current song.")
async def loopsong(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    player.queue.mode = wavelink.QueueMode.loop
    
@bot.command(name="LoopPlaylist",aliases=["loopplaylist","LP","lp","loop","Loop","l","L"], help="Toggles looping of the entire playlist. When enabled, the entire playlist will repeat.", brief="Toggle looping of the playlist.")
async def loopplaylist(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    player.queue.mode = wavelink.QueueMode.loop_all
 
@bot.command(name="Unloop",aliases=["unloop","UnLoop","UL","ul"], help="Disables looping. Songs will play only once without repeating.",brief="Disable looping.")
async def unloop(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    player.queue.mode = wavelink.QueueMode.normal
 

#Autoplay
@bot.command(name="AutoPlay", aliases=["auronplay", "AP","ap","autoplay","Autoplay"],help="Enables or disables autoplay mode. When enabled, the bot will automatically queue and play related songs after the current one finishes.",brief="Enable or disable autoplay mode.")
async def autoplay(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    if player.autoplay == wavelink.AutoPlayMode.enabled:
        player.autoplay = wavelink.AutoPlayMode.partial
    else:
        player.autoplay = wavelink.AutoPlayMode.enabled
    
    await ctx.send(f"AutoPlayMode changed to {player.autoplay}")

    
@bot.command(name="UnAutoPlay", aliases=["unauronplay", "UAP", "DAutoplay","uap","Unautoplay"], help="Disable autoplay, songs will not keep playing after one finishes nor related ones will be queued. (Manually playing a new song will restore songs playing automatically after one finishes)", brief="Disable autoplay mode")
async def unautoplay(ctx):
    player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
    if not player:
        return
    
    player.autoplay = wavelink.AutoPlayMode.disabled 
    await ctx.send("Autoplay Disabled")
 
#playlist spotify 
#config command prefix

#Missing data persistence on setup
#Missing data persistence on prefix
#improve queue visual representation
#help category
#setup help
#prefix help

#source property indicates if YT or Spotify
 
bot.run(token)