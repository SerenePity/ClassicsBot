from discord.ext import commands
import discord
import time
import robotic_roman


class Scholasticus(commands.Bot):

    def __init__(self, prefix):
        super().__init__(command_prefix=prefix)
        self.robot = robotic_roman.RoboticRoman()
        self.quotes_commands = dict()
        self.markov_commands = dict()
        self.authors = list()

    def sleep_for_n_seconds(self, n):
        time.sleep(n - ((time.time() - self.start_time) % n))

    async def on_ready(self):
        print('Logged on as', self.user)
        self.robot.load_all_models()
        self.authors = [self.robot.format_name(person) for person in list(self.robot.quotes_dict.keys()) + list(self.robot.greek_quotes_dict.keys())]
        for author in self.authors:
            self.markov_commands[f"as {author.lower()} allegedly said:"] = author
            self.quotes_commands[f"as {author.lower()} said:"] = author
        print('Done initializing')

    async def on_message(self, message):
        # potential for infinite loop if bot responds to itself
        if message.author == self.user:
            return

        channel = message.channel
        content = message.content

        if content.strip().lower() in self.markov_commands:
            person = self.markov_commands[content.strip().lower()]
            try:
                await self.send_message(channel, self.robot.make_sentence(person.lower()))
            except Exception as e:
                print(e)
                if not person:
                    await self.send_message(channel, "No person provided")
                else:
                    await self.send_message(channel, "I do not have a Markov model for " + self.robot.format_name(person))

        if content.strip().lower() in self.quotes_commands:
            person = self.quotes_commands[content.strip().lower()]
            try:
                await self.send_message(channel, self.robot.random_quote(person.lower()))
            except Exception as e:
                print(e)
                if not person:
                    await self.send_message(channel, "No person provided")
                else:
                    await self.send_message(channel, "I do not have quotes for " + self.robot.format_name(person))

        if content.lower().startswith(self.command_prefix + 'latinquote'):
            await self.send_message(channel, self.robot.pick_random_quote())

        if content.lower().startswith(self.command_prefix + 'greekquote'):
            await self.send_message(channel, self.robot.pick_greek_quote())

        if content.lower().startswith(self.command_prefix + 'helpme'):
            await self.send_message(channel, self.robot.help_command())

        if content.lower().startswith(self.command_prefix + 'latinauthors'):
            await self.send_message(channel, '```'+ '—'.join([self.robot.format_name(a) for a in sorted(self.robot.quotes_dict.keys())]) + '```')

        if content.lower().startswith(self.command_prefix + 'greekauthors'):
            await self.send_message(channel, '```'+ '—'.join([self.robot.format_name(a) for a in sorted(self.robot.greek_quotes_dict.keys())]) + '```')
