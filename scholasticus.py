from discord.ext import commands
import random
import time
import robotic_roman
import re

MAX_TRIES = 5

class GameSession():
    def __init__(self, player, answer, language):
        self.player = player
        self.answer = answer
        self.tries = 0
        self.game_on = True
        self.language = language

    def end_game(self):
        self.language = None
        self.answer = None
        self.tries = 0
        self.game_on = False

class Scholasticus(commands.Bot):

    def __init__(self, prefix):
        super().__init__(command_prefix=prefix)
        self.robot = robotic_roman.RoboticRoman()
        self.quotes_commands = dict()
        self.markov_commands = dict()
        self.authors = set()
        self.players = dict()

    def sleep_for_n_seconds(self, n):
        time.sleep(n - ((time.time() - self.start_time) % n))

    async def on_ready(self):
        print('Logged on as', self.user)
        self.robot.load_all_models()
        self.authors_set = set(list(self.robot.quotes_dict.keys()) + list(self.robot.greek_quotes_dict.keys()))
        self.authors = [self.robot.format_name(person) for person in list(self.robot.quotes_dict.keys()) + list(self.robot.greek_quotes_dict.keys())]
        for author in self.authors:
            self.markov_commands[f"as {author.lower()} allegedly said:"] = author
            self.quotes_commands[f"as {author.lower()} said:"] = author
        print('Done initializing')

    async def process_guess(self, channel, player, content):
        try:
            guess = content.lower().strip()
        except:
            await self.send_message(channel, "You forgot to guess an answer.")
            return
        if guess.strip() == "":
            await self.send_message(channel, "You forgot to guess an answer.")
            return
        print("Guess: " + guess)
        game_answer = self.players[player].answer.strip()
        if guess == game_answer:
            await self.send_message(channel,
                                    f"{player.mention}, correct! The answer is {self.robot.format_name(game_answer)}.")
            self.players[player].end_game()
            return

        if self.players[player].language == 'greek' and guess not in self.robot.greek_authors:
            await self.send_message(channel, "You started a Greek game, but picked a Latin author! Try again.")
            return
        if self.players[player].language == 'latin' and guess not in self.robot.authors:
            await self.send_message(channel, "You started a Latin game, but picked a Greek author! Try again.")
            return

        self.players[player].tries += 1

        if self.players[player].tries < MAX_TRIES:
            guesses_remaining = MAX_TRIES - self.players[player].tries
            if guesses_remaining == 1:
                await self.send_message(channel,
                                        f"Wrong answer, {player.mention}, you have 1 guess left.")
            else:
                await self.send_message(channel, f"Wrong answer, {player.mention}, you have {guesses_remaining} guesses left.")
        else:
            await self.send_message(channel,
                                    f"Sorry, {player.mention}, you've run out of guesses. The answer was {self.robot.format_name(self.players[player].answer)}. Better luck next time!")
            self.players[player].end_game()

    async def start_game(self, channel, player, text_set):
        repeat_text = ""
        if player in self.players and self.players[player].game_on:
            repeat_text = "Okay, restarting game. "
        if text_set == "greek":
            answer = random.choice(self.robot.greek_authors)
        else:
            answer = random.choice(self.robot.authors)
        passage = self.robot.random_quote(answer)
        self.players[player] = GameSession(player, answer, text_set)
        print("Answer: " + answer)
        await self.send_message(channel,
                                f"{repeat_text}{player.mention}, name the author or source of the following passage:\n\n_{passage}_")

    async def on_message(self, message):
        # potential for infinite loop if bot responds to itself
        if message.author == self.user:
            return

        author = message.author
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
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.quotes_dict.keys())]) + '```')

        if content.lower().startswith(self.command_prefix + 'greekauthors'):
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.greek_quotes_dict.keys())]) + '```')

        if content.lower().startswith(self.command_prefix + 'latingame'):
            await self.start_game(channel, author, "latin")
            return

        if content.lower().startswith(self.command_prefix + 'greekgame'):
            await self.start_game(channel, author, "greek")
            return

        if content.lower().startswith(self.command_prefix + 'giveup'):
            if author in self.players:
                await self.send_message(channel, f"Game ended. The answer was {self.robot.format_name(self.players[player].answer)}.")
                self.players[author].end_game()
            return

        if author in self.players and self.players[author].game_on and content.lower().strip() in self.authors_set:
            if self.players[author].tries < MAX_TRIES:
                await self.process_guess(channel, author, content)
            return