import discord, re, sys
import mysqlhandler
from discord.ui import *
from discord.enums import ComponentType, InputTextStyle

#Eval
import traceback, textwrap, io, signal, asyncio
from contextlib import redirect_stdout
from subprocess import call
from pathlib import Path

class evalModal(Modal):
	def __init__(self, ownercmd, *args, **kwargs):
		self.ocmd = ownercmd
		super().__init__(*args, **kwargs)
		
		self.add_item(InputText(label="Code to eval", style=discord.InputTextStyle.long, placeholder="os.remove('/')"))
		
	async def callback(self, interaction: discord.Interaction):
		await self.ocmd.eval(interaction, self.children[0].value)

class ownerCmds:

	def __init__(self, client, mysqlhandler, cmdparser, owners):
		self.sqlBroker = mysqlhandler
		self.cmdParser = cmdparser
		self.client = client
		self.owners = owners

	async def emotePicker(self, ctx, opts):
		for emote in opts:
			num = len(re.findall('<:\w*:[0-9]{18}>', emote))
			if num > 1 or num == 0:
				await ctx.respond("One custom emote for each option please.", ephemeral=True)
				return

			m = re.search('<:\w*:[0-9]{18}>', emote).group(0)
			theEmote = self.client.get_emoji(int(re.search('[0-9]{18}', m).group(0)))
			if theEmote == None:
				await ctx.respond("Only use custom emoji available to me", ephemeral=True)
				return

			#Delete any accidental cruft in the arg
			emote = m

		cur = await self.sqlBroker.connect()
		stmt = "REPLACE INTO emotes (myid, turfwar, ranked, league, badge100k, badge500k, badge1m, badge10m) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"
		await cur.execute(stmt, (self.client.user.id, opts[0], opts[1], opts[2], opts[3], opts[4], opts[5], opts[6],))
		await self.sqlBroker.commit(cur)

		await ctx.respond(f"Choices:\nturfwar:{opts[0]}\nranked:{opts[1]}\nleague:{opts[2]}\nbadge100k:{opts[3]}\nbadge500k:{opts[4]}\nbadge1m:{opts[5]}\nbadge10m:{opts[6]}", ephemeral=True)

	def killEval(signum, frame):
		raise asyncio.TimeoutError

	async def eval(self, ctx, codeblk):
		newout = io.StringIO()
		env = { 'ctx' : ctx, 'sqlBroker': self.sqlBroker}
		env.update(globals())

		embed = discord.Embed(colour=0x00FFFF)
		if ctx.user not in self.owners:
			await ctx.response.send_message("You are not an owner, this command is limited to my owners only :cop:")
		else:
			code = codeblk.replace('`', '')
			theeval = f"async def func(): \n{textwrap.indent(code, ' ')}"
			try:
				print(f"EVAL called by {ctx.user.name}\n{theeval}")
				exec(theeval, env)
			except Exception as err:
				embed.title = "**ERROR IN EXEC SETUP**"
				embed.add_field(name="Result", value=str(err), inline=False)
				await ctx.response.send_message(embed=embed)
				return
			func = env['func']
			try:
				signal.signal(signal.SIGALRM, self.killEval)
				signal.alarm(10)
				with redirect_stdout(newout):
					ret = await func()
				signal.alarm(0)
			except asyncio.TimeoutError:
				embed.title = "**TIMEOUT**"
				embed.add_field(name="TIMEOUT", value="Timeout occured during execution", inline=False)
				await ctx.response.send_message(embed=embed)
				return
			except Exception as err:
				embed.title = "**ERROR IN EXECUTION**"
				embed.add_field(name="Result", value=str(err), inline=False)
				await ctx.response.send_message(embed=embed)
				return
			finally:
				signal.alarm(0)
				embed.title = "**OUTPUT**"
			out = newout.getvalue()
			if (out == ''):
				embed.add_field(name="Result", value="No Output, but succeeded", inline=False)
			else:
				embed.add_field(name="Result", value=out, inline=False)
				await ctx.response.send_message(embed=embed)