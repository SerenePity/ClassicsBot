import random
import re
import shlex
import traceback

import discord
from lang_trans.arabic import arabtex
import romanize3
from transliterate import translit

from bible_compare.int_prefixed_books import get_int_prefix_book
from char_lookup import lookup_wikt
import my_wiktionary_parser
from robot_brain import QuoteContext, RobotBrain
import transliteration.coptic
import transliteration.greek
import transliteration.hebrew
import transliteration.korean
import transliteration.mandarin
import transliteration.middle_chinese
import transliteration.old_chinese
import transliteration.japanese

MAX_TRIES = 5
BOT_OWNER = 285179803819311106

NEWCOMER_ID = 716979211549540403
POMERIUM_CHANNEL_ID = 716979999172853890
POMERIUM_NOTIFICATIONS_CHANNEL_ID = 783851454514462730
POMERIUM_MESSAGE_THRESHOLD = 3

DISCORD_CHAR_LIMIT = 2000
LATIN_SERVER_ID = 333434240610074627
TOGAM_GERENS_ROLE = 973986410048667718

robot = RobotBrain("")


class PlayerSession:
    """
    Class to simulate a player's game session
    """


    def __init__(self, player, answer, language, channel):
        self.player = player
        self.answer = answer
        self.tries = 0
        self.game_on = True
        self.language = language
        self.channel = channel


    def end_game(self):
        self.language = None
        self.answer = None
        self.tries = 0
        self.game_on = False
        self.channel = None


class Game:
    """
    Class to simulate a game, which can be of multiple types
    """


    def __init__(self, game_owner, answer, language, channel, is_word_game=False, is_grammar_game=False,
                 word_language='latin', hint=None, is_shuowen_game=False):
        self.game_owner = game_owner
        self.game_on = True
        self.players_dict = dict()
        self.language = language
        self.channel = channel
        self.answer = answer
        self.exited_players = set()
        self.is_word_game = is_word_game
        self.is_grammar_game = is_grammar_game
        self.is_shuowen_game = is_shuowen_game
        self.word_language = word_language
        self.hint = hint
        self.players_dict[game_owner] = PlayerSession(game_owner, answer, language, channel)


    def get_game_owner_sess(self):
        return self.players_dict[self.game_owner]


    def add_player(self, player):
        """
        Add a player to the current game

        :param player: the Member object of the player to be added
        :return:
        """
        self.players_dict[player] = PlayerSession(player, self.answer, self.language, self.channel)


    def get_player_sess(self, player):
        """
        Get the PlayerSession associated with the player

        :param player: the Member object of the player whose PlayerSession is to be retrieved
        :return: the PlayerSession associated with player
        """
        return self.players_dict[player]


    def end_player_sess(self, player):
        """
        Ends the game for the given player

        :param player: the player (of type Member) whose game session we want to end
        :return:
        """
        self.exited_players.add(player)
        if player in self.players_dict:
            self.players_dict[player].end_game()
        del self.players_dict[player]


    def no_players_left(self):
        """
        Check if there are no players left in the game
        """
        return all(not self.players_dict[player].game_on for player in self.players_dict)


    def get_hint(self):
        """
        Return an answer hint
        """
        return self.hint


    def end_game(self):
        """
        Ends the game session and resets all data members to default values
        """
        self.language = None
        self.word_language = None
        self.answer = None
        self.game_on = False
        self.channel = None
        self.is_word_game = False
        self.exited_players = set()
        self.players_dict = dict()


# noinspection PyTypeHints
class ClassicsBot(discord.Client):
    """
    Represents a bot connection that connects to Discord. Inherits from the discord.Client class.
    """


    def __init__(self, prefix=""):
        super().__init__(command_prefix=prefix)
        self.robot = robot
        self.quotes_commands = dict()
        self.markov_commands = dict()
        self.authors = set()
        self.games = dict()
        self.players_to_game_owners = dict()
        self.quote_requestors = dict()
        self.command_dict = dict()
        self.command_prefix = prefix
        self.authors_set = set()


    async def is_nsfw(self, channel):
        """
        Check if a channel is NSFW
        :param channel: a channel object
        :return: True if the channel is NSFW, else False
        """
        try:
            _gid = channel.server.id
        except AttributeError:
            return False
        data = await self.http.request(
            discord.http.Route(
                'GET', '/guilds/{guild_id}/channels', guild_id=_gid))
        channeldata = [d for d in data if d['id'] == channel.id][0]
        return channeldata['nsfw']


    async def on_ready(self):
        """
        Some methods to call when the bot has finished initializing
        """
        print('Logged on as', self.user)
        activity = discord.Game(name="helpme for help", type=3)
        self.robot.load_all_models()
        for authors in self.robot.authors_collection:
            for author in authors:
                self.authors_set.add(author)

        # self.authors_set.add('reddit')
        self.authors = [self.robot.format_name(person) for person in self.authors_set]
        print('Done initializing')


    def sanitize_user_input(self, text):
        """
        Remove the ',', '!', ':', and ';' characters from a string
        """
        return text.replace(',', '').replace('!', '').replace(':', '').replace(';', '')


    def language_format(self, language):
        """
        Reformat language input. If no language is provided, default to "latin." If "greek" is provided, default to
        "ancient greek". If "modern greek" or "modern_greek" is the input, default to "greek," as Modern Greek entries
        are listed simply under "Greek" in Wiktionary. All input is case-insensitive.
        """
        if not language:
            return 'latin'
        if language.lower() == 'greek':
            return 'ancient greek'
        if language.lower().replace('_', ' ') == 'modern greek':
            return 'greek'
        return language


    async def process_guess(self, channel, player, content, word_game=False):
        """
        Process a guess in a game.

        :param channel: the channel in which the guess was made
        :param player: the player who made the guess
        :param content: the guess itself
        :param word_game: whether or not the current game is a word game--if it is, the guess is case-sensitive
        :return: send a message in the channel informing the player of the outcome of their guess
        """
        try:
            if not word_game:
                guess = content.lower().strip()
            else:
                guess = content.strip()
        except:
            await channel.send("You forgot to guess an answer.")
            return
        if guess.strip() == "":
            await channel.send("You forgot to guess an answer.")
            return
        print("Guess: " + guess)
        game_owner = self.players_to_game_owners[player]
        game_answer = self.games[game_owner].answer.strip()
        print(f"Is wordgame {word_game}")
        print(f"Is grammargame {self.games[game_owner].is_grammar_game}")
        formatted_answer = self.robot.format_name(game_answer) if not (
                word_game or self.games[game_owner].is_grammar_game) else game_answer.split('/')[-1]
        if guess.lower() == game_answer.lower().split('/')[-1]:
            await channel.send(f"{player.mention}, correct! The answer is {formatted_answer}.")
            self.games[game_owner].end_game()
            return
        if self.games[game_owner].language in ['greek', 'latin']:

            if self.games[game_owner].language == 'greek' and guess not in self.robot.greek_authors and guess != 'hint':
                await channel.send(
                    "You did not pick a valid author for this game! For a list of valid authors, type 'greekauthors'.")
                return
            if self.games[game_owner].language == 'latin' and guess not in self.robot.latin_authors and guess != 'hint':
                await channel.send(
                    "You did not pick a valid author for this game! For a list of valid authors, type 'latinauthors'.")
                return

        self.games[game_owner].get_player_sess(player).tries += 1

        if self.games[game_owner].players_dict[player].tries < MAX_TRIES:
            guesses_remaining = MAX_TRIES - self.games[game_owner].players_dict[player].tries
            if guess.strip().lower() == "hint" and self.games[game_owner].is_word_game:
                etymology = self.robot.get_word_etymology(game_answer, self.games[game_owner].word_language).strip()
                await channel.send(
                    f"{player.mention}, you've sacrificed a guess to get the following etymology of the word:\n\n{etymology}\n\nYou now have have {guesses_remaining} {'guesses' if guesses_remaining > 1 else 'guess'} left.")
            elif self.games[game_owner].is_shuowen_game:
                hint = self.games[game_owner].get_hint()
                await channel.send(
                    f"{player.mention}, you've sacrificed a guess to get the following Mandarin pinyin pronunciation of the word:\n\n{hint}\n\nYou now have have {guesses_remaining} {'guesses' if guesses_remaining > 1 else 'guess'} left.")
            elif not self.games[game_owner].is_word_game and guess.strip().lower() == "hint":
                await channel.send("No hints.")
            else:
                await channel.send(
                    f"Wrong answer, {player.mention}, you have {guesses_remaining} {'guesses' if guesses_remaining > 1 else 'guess'} left.")
        else:
            self.games[game_owner].players_dict[player].end_game()
            if self.games[game_owner].no_players_left():
                if len(self.games[game_owner].players_dict) == 1:
                    await channel.send(
                        f"Sorry, {player.mention}, you've run out of guesses. The answer was {formatted_answer}. Better luck next time!")
                else:
                    await channel.send(
                        f"Everybody has run out of guesses. The answer was {formatted_answer}. Better luck next time!")
                self.end_game(game_owner)
                # self.games[game_owner].end_game()
            else:
                await channel.send(
                    f"Sorry, {player.mention}, you've run out of guesses! Better luck next time!")
                self.games[game_owner].get_player_sess(player).end_game()
                self.games[game_owner].exited_players.add(player)
                del self.players_to_game_owners[player]


    async def start_game(self, channel, game_owner, language, is_text_game=False, is_word_game=False,
                         is_grammar_game=False, is_shuowen_game=False, macrons=False):

        instruction = "\n\nType g <answer> to guess your answer. Type giveup to give up."
        repeat_text = ""
        answer = ""
        hint = None
        if game_owner in self.games and self.games[game_owner].game_on:
            repeat_text = "Okay, restarting game."
        if is_text_game:
            if language == "greek":
                answer = random.choice(self.robot.greek_authors)
            elif language == "latin":
                answer = random.choice(self.robot.latin_authors)
            elif language == "chinese":
                answer = random.choice(self.robot.chinese_authors)
            _, passage, _ = self.robot.random_quote(answer)
            await channel.send(
                f"{repeat_text}{game_owner.mention}, name the author or source of the following passage:\n\n_{passage}_{instruction}")
        elif is_grammar_game:
            grammar_game_set = my_wiktionary_parser.get_grammar_question(language)
            answer = grammar_game_set[0]
            grammar_question = random.choice(grammar_game_set[1]).strip()
            grammar_question = grammar_question[0].lower() + grammar_question[1:]
            lemma = my_wiktionary_parser.remove_macrons(grammar_question.split(' ')[-1]).replace('.', '')
            answer_def = robot.get_word_definitions(lemma, language, False)[0].split('\n')[0]
            # print("Answer def:\n\n" + answer_def)
            question = "Name the " + grammar_question + ' [definition: ' + answer_def + ']'
            if not macrons:
                answer = my_wiktionary_parser.remove_macrons(answer)
            await channel.send(
                f"{repeat_text}{game_owner.mention}, {question}{instruction}")
        elif is_word_game:
            answer = self.robot.get_random_word(language).strip()
            definition = self.robot.get_and_format_word_defs(answer, language, include_examples=False)
            await channel.send(
                f"{repeat_text}{game_owner.mention}, name the {language.title()} word (in lemma form) with the "
                f"following definitions:\n\n{definition}{instruction}")
        elif is_shuowen_game:
            answer, passage, hint = self.robot.shuowen_game()
            await channel.send(
                f"{repeat_text}{game_owner.mention}, type the character with the following entry in Shuowen Jiezi: {passage}{instruction}")
        self.games[game_owner] = Game(game_owner, answer, language, channel, is_word_game, is_grammar_game,
                                      word_language=language, hint=hint)
        self.players_to_game_owners[game_owner] = game_owner
        print("Answer: " + answer)


    def end_game(self, game_owner):
        """
        Ends the current game
        """
        game = self.games[game_owner]
        for player in game.players_dict:
            if player in self.players_to_game_owners:
                del self.players_to_game_owners[player]
        del self.games[game_owner]


    @staticmethod
    async def send_truncate(channel, text):
        """
        Truncate if text is longer than the Discord character limit
        :param channel: the channel to send the message in
        :param text: the text to send
        :return:
        """
        if len(text) > DISCORD_CHAR_LIMIT:
            truncation_text = "... (text truncated)"
            await channel.send(text[:1500] + truncation_text)
        else:
            await channel.send(text)


    async def send_in_chunks_if_needed(self, channel, text, n=2000):
        """
        Send a message in chunks if it exceeds a certain length.
        :param channel: the channel in which to send the message(s)
        :param text: the text to be sent
        :param n: the maximum size of each chunk, set by default to 2000, which is the maximum length of a Discord message
        """
        if len(text) > DISCORD_CHAR_LIMIT:
            chunks = RobotBrain.chunks(text, n)
            for chunk in chunks:
                await channel.send(chunk)
        else:
            await channel.send(text)


    def format_chapter_for_gibbon(self, chapter):
        """
        Return the chapter title for Gibbon's Decline and Fall of the Roman Empire
        :param chapter:
        :return:
        """
        if "chapter" not in chapter and chapter.lower() != "preface":
            chapter_number = re.findall(r"[0-9]+", chapter)
            if len(chapter_number) > 0:
                chapter = f"Chapter {chapter_number[0]}"
                return chapter
        else:
            return chapter.title()


    async def on_member_update(self, before, after):
        # FIXME: not entirely sure this works anymore.
        """
        Send a message to new users when they are approved to join the server (i.e, when the "Newcomer" role is removed
        """
        newcomer_role = discord.utils.get(before.roles, id=NEWCOMER_ID)
        try:
            if newcomer_role in before.roles and newcomer_role not in after.roles:
                pm_channel = await self.start_private_message(after)
                await self.send_message(pm_channel,
                                        f"Welcome {after.mention} to the Latin server. In order to ensure an "
                                        f"atmosphere agreeable to all, please be sure to observe the following rules: "
                                        "\n\n**I.** Treat others with respect at all times. Personal insults will "
                                        "not be tolerated. Tread carefully when discussing sensitive issues. "
                                        "\n\n**II.** No slurs or hate speech. Do not hide hate speech under the "
                                        "pretense of humour. This is a place for people of all backgrounds. "
                                        "\n\n**III.** Keep images and text generally SFW. If you wouldn't show it "
                                        "to your Latin teacher, do not show it to us. "
                                        "\n\n**IV.** No spam. Do not abuse pings."
                                        "\n\nWe operate within a three-strikes system. You will be warned for your "
                                        "first three infractions, after which you will be automatically banned. In "
                                        "egregious cases, we may skip straight to the ban. "
                                        "\n\nThe rules are enforced according to our discretion. Do not challenge a "
                                        "warning. If you're confused, you may contact an Imperator privately. "
                                        "\n\n_If something in the chat concerns you, please ping the "
                                        "***@Imperator*** role or message an Imperator directly._")
        except:
            traceback.print_exc()


    async def on_message(self, message):
        """
        Called when a message is created and sent

        :param message:
        :return:
        """
        # potential for infinite loop if bot responds to itself
        if message.author == self.user:
            return

        author = message.author
        channel = message.channel
        content = message.content

        """
        Send a message in the Pomerium Notifications channel users when a Newcomer types a message in the Pomerium of 
        length greater than 15 characters.
        """
        if channel.id == 975146010038910996:
            newcomer_role = discord.utils.get(author.roles, id=NEWCOMER_ID)
            if newcomer_role and len(
                    content.split()) > POMERIUM_MESSAGE_THRESHOLD:
                try:
                    await author.remove_roles(newcomer_role, atomic=True)

                    pomerium_notifications_channel = self.get_channel(POMERIUM_NOTIFICATIONS_CHANNEL_ID)
                    newlines = content.split('\n')
                    content_str = '\n'.join(['> ' + line for line in newlines])
                    print(f"New user {author.mention} has answered the Pomerium prompt:\n" +
                          content_str)
                    await pomerium_notifications_channel.send(
                        f"New user {author.mention} has answered the Pomerium prompt:\n" +
                        content_str)
                except:
                    traceback.print_exc()

        if content.lower().startswith(self.command_prefix + 'getdef'):
            args = shlex.split(content.replace('“', '"').replace('”', '"').strip())
            try:
                if len(args) < 3:
                    await channel.send("Error: you must specify a language to get the word definition(s)")
                    return
                if len(args) > 1:
                    language = args[1]
                    word = ' '.join(args[2:])
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    language = self.language_format(language)
                    definition = self.robot.get_and_format_word_defs(word, language, include_examples=False)
                else:
                    definition = "Invalid arguments"
                await self.send_in_chunks_if_needed(channel, definition)
                return
            except discord.errors.HTTPException:
                traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await channel.send(f"The entry is too long. Here's the URL instead: {url}")
            except:
                traceback.print_exc()
                await channel.send("An error occurred while trying to retrieve the definition.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'randword') or content.lower().startswith(
                self.command_prefix + 'randomword'):
            args = shlex.split(content.replace('“', '"').replace('”', '"').strip())
            language = ""

            try:

                if len(args) == 1:
                    word = self.robot.get_random_word('latin')
                    await self.send_truncate(channel, self.robot.get_full_entry(word, 'latin'))
                    return
                elif len(args) > 1:
                    language = ' '.join(args[1:])
                    language = self.language_format(language)
                    word = self.robot.get_random_word(language)
                    entry = self.robot.get_full_entry(word, language)
                    await self.send_truncate(channel, entry)
                    return
            except discord.errors.HTTPException:
                # traceback.print_exc()
                if 'proto-' in language.lower():
                    url = f"https://en.wiktionary.org/wiki/{word}"
                else:
                    url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await channel.send(f"The entry is too long. Here's the URL instead: {url}")
            except:
                # traceback.print_exc()
                await channel.send("An error occurred while trying to retrieve the word.")
                return
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + "getety"):
            args = shlex.split(content.replace('“', '"').replace('”', '"').strip())

            try:
                if len(args) < 3:
                    await channel.send("Error: you must specify a language to get the word etymology")
                    return
                if len(args) > 1:
                    language = args[1]
                    word = ' '.join(args[2:])
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    language = self.language_format(language)
                    etymology = self.robot.get_word_etymology(word, language)
                else:
                    etymology = "Invalid arguments"
                await self.send_truncate(channel, etymology)
                return
            except discord.errors.HTTPException:
                # traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await channel.send(f"The entry is too long. Here's the URL instead: {url}")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + "getentry"):
            args = shlex.split(content.replace('“', '"').replace('”', '"').strip())

            try:
                if len(args) < 3:
                    await channel.send("Error: you must specify a language to get the word entry")
                    return
                if len(args) > 1:
                    language = args[1]
                    language = self.language_format(language)
                    word = ' '.join(args[2:])
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    entry = self.robot.get_full_entry(word, language)
                else:
                    entry = "Invalid arguments"
                await self.send_truncate(channel, entry)
                return
            except discord.errors.HTTPException:
                # traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await channel.send(f"The entry is too long. Here's the URL instead: {url}")
            except:
                # traceback.print_exc()
                await channel.send("An error occurred while trying to retrieve the word entry.")
                return
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'char_origin'):
            args = shlex.split(content.replace('“', '"').replace('”', '"').strip())
            char = args[1]
            soup = my_wiktionary_parser.get_soup(char)
            glyph_origin = my_wiktionary_parser.get_glyph_origin(soup, list(char))
            await channel.send(glyph_origin)
            return

        # ==================================================================================================================================================

        """if content.lower().startswith(self.command_prefix + 'redditquote'):
            
            try:
                subreddit = shlex.split(content.lower().strip())[1]
                await self.send_in_chunks_if_needed(channel, self.robot.reddit_quote(subreddit))
            except:
                traceback.print_exc()
                await channel.send("Error. Subreddit possibly doesn't exist.")"""

        # ==================================================================================================================================================

        # Removed random reddit post command
        """
        if content.lower().startswith(self.command_prefix + 'redditquote') or content.lower().startswith(self.command_prefix + 'git '):
            
            try:
                subreddit = shlex.split(content.lower().strip())[1]
                subreddit_obj = self.robot.reddit.subreddit(subreddit)
                channel_nsfw = await self.is_nsfw(channel)
                print(f"channel is nsfw: {channel_nsfw}")
                if not channel_nsfw and subreddit_obj.over18:
                    await channel.send("Cannot retrieve posts from an Over 18 subreddit in this channel.")
                else:
                    await self.send_in_chunks_if_needed(channel, self.robot.reddit_quote(subreddit_obj))
            except:
                #traceback.print_exc()
                await channel.send("Error. Subreddit possibly doesn't exist.")
        """
        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'bibleversions'):
            args = shlex.split(content.lower())
            if len(args) > 1:
                language = ' '.join(args[1:]).lower()
                ret_list = self.robot.get_available_bible_versions_lang(language)
                try:
                    for version in ret_list:
                        await channel.send(version)
                except discord.errors.HTTPException:
                    # traceback.print_exc()
                    await channel.send(f"The entry is too long. Here's the URL instead: {url}")
                except:
                    # traceback.print_exc()
                    await channel.send(
                        "Invalid language. Type '>bibleversions' for get available versions for all languages.")
            else:
                try:
                    await channel.send(self.robot.get_available_bible_versions())
                except discord.errors.HTTPException:
                    # traceback.print_exc()
                    await channel.send(f"Text is too long.")

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'tr '):
            # if message.author.id == '506033040288645131' or message.server.id == '580907126499835925':
            #    await self.send_message(message.channel, "Long Live Great Kurdistan! Happyfeet is lame.")
            #   return

            try:
                tr_args = shlex.split(content)
            except:
                await channel.send("Error, no closing quotation. Please try to enclose the input within quotes.")
                return
            if len(tr_args) > 2:
                language = tr_args[1].lower()
            else:
                await channel.send("Invalid arguments.")
            try:
                input = ' '.join(tr_args[2:])
                if language == '-gre':
                    transliterated = transliteration.greek.transliterate(input)
                if language == '-heb':
                    transliterated = transliteration.hebrew.transliterate(input)
                elif language == '-cop':
                    transliterated = transliteration.coptic.transliterate(input)
                elif language == '-oc':
                    transliterated = transliteration.old_chinese.transliterate(input)
                elif language == '-mc':
                    transliterated = transliteration.middle_chinese.transliterate(input)
                elif language == '-mand':
                    transliterated = transliteration.mandarin.transliterate(input)
                elif language == '-aram':
                    r = romanize3.__dict__['arm']
                    transliterated = r.convert(input)
                elif language == '-arab':
                    transliterated = arabtex.transliterate(input)
                elif language == '-syr':
                    r = romanize3.__dict__['syc']
                    transliterated = r.convert(input)
                elif language == '-arm':
                    transliterated = translit(input, 'hy', reversed=True).replace('ւ', 'v')
                elif language == '-geo':
                    transliterated = translit(input, 'ka', reversed=True).replace('ჲ', 'y')
                elif language == '-rus':
                    transliterated = translit(input, 'ru', reversed=True)
                elif language == '-kor':
                    transliterated = transliteration.korean.transliterate(input)
                elif language == '-jap':
                    transliterated = transliteration.japanese.transliterate(input)
                else:
                    transliterated = transliteration.greek.transliterate(input)
                await self.send_in_chunks_if_needed(channel, transliterated)
                return
            except Exception as e:
                # traceback.print_exc()
                await channel.send(f"Error transliterating input.")
                return

        # ==================================================================================================================================================

        # Consider removing.
        if content.lower().startswith(self.command_prefix + 'textend') or content.lower().startswith(
                self.command_prefix + 'txtend'):
            del self.quote_requestors[author]
            self.quote_requestors[author] = None
            return

        # ==================================================================================================================================================

        # Consider removing.
        if content.lower().startswith(self.command_prefix + 'textstart') or content.lower().startswith(
                self.command_prefix + 'tstart'):
            args = shlex.split(content.lower())

            if len(args) < 2:
                await channel.send("You must provide an author or work.")
            else:
                source = ' '.join(args[1:])
                if source not in self.authors_set:
                    source = "the " + source.strip().lower()
                display, workslist = self.robot.show_author_works(source)
                # print("Display: " + str(display))
                # print("Workslist: " + str(workslist))
                qt_obj = QuoteContext(source, [], 0, workslist)
                self.quote_requestors[author] = qt_obj
                if len(display) > 2000:
                    parts = list(RobotBrain.chunks(display, 10))
                    for part in parts:
                        await channel.send(' '.join(part))
                else:
                    await channel.send(display)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'biblecompare'):

            qt_args = shlex.split(content)
            # print(qt_args)
            arg_str = " ".join(qt_args)
            int_prefixed_book = get_int_prefix_book(arg_str)
            try:
                if int_prefixed_book:
                    verse = int_prefixed_book + ' ' + qt_args[3]
                    versions = qt_args[4:]
                elif len(qt_args) > 4 and qt_args[1].isdigit():
                    verse = ' '.join([qt_args[1], qt_args[2], qt_args[3]])
                    versions = qt_args[4:]
                elif len(qt_args) > 2 and re.match(r"[0-9]+:[0-9]+", qt_args[2]):
                    verse = qt_args[1] + ' ' + qt_args[2]
                    # print("Verse: " + verse)
                    versions = qt_args[3:]
                else:
                    await channel.send("Invalid arguments.")
                    return
                print(f"Getting verse: {verse}, for {', '.join(versions)}")
                translation = self.robot.bible_compare(verse, versions)
                await channel.send(translation)
                return
            except discord.errors.HTTPException:
                # traceback.print_exc()
                await channel.send(f"Text is too long.")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'qt'):
            qt_args = shlex.split(content.replace('“', '"').replace('”', '"'))
            if qt_args[0].lower() != 'qt':
                return
            # print(qt_args)
            word = None
            transliterate = False
            lemmatize = False
            case_sensitive = False
            author_of_quote = ""
            try:
                for i, arg in enumerate(qt_args):
                    if '-w' in arg.strip().lower():
                        word = qt_args[i + 1]
                        if "l" in arg:
                            lemmatize = True
                        if "c" in arg:
                            case_sensitive = True
                    if arg.strip().lower() == '-t':
                        transliterate = True

                if word and transliterate:
                    author_of_quote = ' '.join(qt_args[4:]).lower().strip()
                    word = self.sanitize_user_input(word)
                elif word and not transliterate:
                    author_of_quote = ' '.join(qt_args[3:]).lower().strip()
                elif transliterate and not word:
                    author_of_quote = ' '.join(qt_args[2:]).lower().strip()
                elif not word and not transliterate:
                    author_of_quote = ' '.join(qt_args[1:]).lower().strip()

                if transliterate:
                    """
                    if source == "reddit":
                        subreddit = self.robot.reddit.random_subreddit(nsfw=False)
                        await self.send_in_chunks_if_needed(channel,
                                                f"From r/{subreddit.display_name}:\n{robot.reddit_quote(subreddit.display_name)}")
                        return
                    """
                    index, quote, quotes_list = self.robot.random_quote(author_of_quote.lower(), word, lemmatize,
                                                                        case_sensitive=case_sensitive)
                    _, works_list = self.robot.show_author_works(author_of_quote)
                    qt_obj = QuoteContext(author_of_quote.lower(), quotes_list, index + 1, works_list)
                    self.quote_requestors[author] = qt_obj
                    transliterated = transliteration.greek.transliterate(quote)
                    await channel.send(transliterated)
                    return
                else:
                    """
                    if source == "reddit":
                        subreddit = self.robot.reddit.random_subreddit(nsfw=False)
                        #print(subreddit.display_name)
                        await self.send_in_chunks_if_needed(channel, f"From r/{subreddit.display_name}:\n{robot.reddit_quote(subreddit.display_name)}")
                        return
                    """
                    index, quote, quotes_list = self.robot.random_quote(author_of_quote.lower(), word, lemmatize,
                                                                        case_sensitive=case_sensitive)
                    quote = re.sub(r"([?!])\s*\.", r"\1", quote)
                    _, works_list = self.robot.show_author_works(author_of_quote)
                    qt_obj = QuoteContext(author_of_quote.lower(), quotes_list, index + 1, works_list=works_list)
                    self.quote_requestors[author] = qt_obj
                    await channel.send(quote)
            except discord.errors.HTTPException:
                traceback.print_exc()
                await channel.send(f"The passage is too long.")
            except Exception as e:
                traceback.print_exc()
                if not author_of_quote:
                    await channel.send("No person provided")
                else:
                    await channel.send(f"Could not find quotes matching criteria.")
            return

        # ==================================================================================================================================================
        """
        if content.lower().startswith(self.command_prefix + 'owo'):
            
            qt_args = shlex.split(content.replace('“','"').replace('”','"'))
            # print(qt_args)
            try:
                author = ' '.join(qt_args[1:]).lower().strip()
                if author.strip() == '':
                    return
                quote = self.robot.random_quote(author.lower())[1]
                if author in self.robot.greek_authors or 'the ' + author.strip() in self.robot.greek_authors:
                    quote = transliteration.greek.transliterate(quote)
                if author in self.robot.chinese_authors or 'the ' + author.strip() in self.robot.chinese_authors :
                    quote = transliteration.mandarin.transliterate(quote)
                output = owo.text_to_owo(quote)
                if len(output.strip()) > 1:
                    await channel.send(output)
                else:
                    await channel.send(f"I do not have quotes for {self.robot.format_name(author)}.")
            except Exception as e:
                traceback.print_exc()
                if not author:
                    await channel.send("No person provided")
                else:
                    await channel.send(f"I do not have quotes for {self.robot.format_name(author)}.")
        """

        if content.lower().startswith(self.command_prefix + 'latinquote'):
            await channel.send(self.robot.pick_random_latin_quote())
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'chinesequote'):
            await channel.send(self.robot.pick_random_chinese_quote())
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'greekquote'):
            args = shlex.split(content.lower())
            transliterate = len(args) > 1 and args[1] == '-t'
            quote = self.robot.pick_greek_quote()
            if transliterate:
                quote = transliteration.greek.transliterate(quote)
            await channel.send(quote)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'germanicquote'):
            await channel.send(self.robot.pick_random_germanic_quote())
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'comm '):

            args = shlex.split(content.lower())
            if len(args) < 2:
                await channel.send("No argument provided")
                return
            else:
                try:
                    i = int(args[1])
                except:
                    await channel.send("Argument must be an integer.")
                await channel.send(f"Type {self.command_dict[i]}")
            return

        # ==================================================================================================================================================

        if content.lower().strip() == self.command_prefix + 'helpme':
            help_list = self.robot.commands
            bot_commands = ['Arguments in <> are required, while those in [] are optional']
            for i in range(len(help_list)):
                desc = help_list[i][0].strip()
                command_format = help_list[i][1].strip()
                self.command_dict[i + 1] = help_list[i][1]
                bot_commands.append(f"**{i + 1}.** *{desc}*: {command_format}")
            bot_commands_text = '\n'.join(bot_commands)
            embed = discord.Embed(title='Classics Bot Usage Guide',
                                  description=bot_commands_text)
            await channel.send(embed=embed)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'latinauthors'):
            await channel.send(
                f"```{', '.join([self.robot.format_name(a) for a in sorted(self.robot.latin_quotes_dict.keys())])}```")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'greekauthors'):
            await channel.send(
                f"```{', '.join([self.robot.format_name(a) for a in sorted(self.robot.greek_quotes_dict.keys())])}```")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'chineseauthors'):
            await channel.send(
                f"```{', '.join([self.robot.format_name(a) for a in sorted(self.robot.chinese_quotes_dict.keys())])}```")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'germanicauthors'):
            await channel.send(
                f"```{', '.join([self.robot.format_name(a) for a in sorted(self.robot.germanic_quotes_dict.keys())])}```")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'shuowengame'):
            await self.start_game(channel, author, "chinese", is_shuowen_game=True)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'wordgame'):
            args = shlex.split(content.lower().replace('“', '"').replace('”', '"'))
            if len(args) > 1:
                language = ' '.join(args[1:]).strip()
                language = self.language_format(language)
            await self.start_game(channel, author, language, is_word_game=True)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'textgame'):
            args = shlex.split(content.lower().replace('“', '"').replace('”', '"'))
            if len(args) > 1:
                language = ' '.join(args[1:]).strip()
                language = self.language_format(language)
                await self.start_game(channel, author, language, is_text_game=True)
                return
            return

        # ==================================================================================================================================================

        if content.lower().startswith('grammargame'):
            args = shlex.split(content.lower())
            macrons = '-m' in content.lower()
            language = ' '.join(args[1:]).strip()
            language = self.language_format(language)
            await self.start_game(channel, author, language, is_grammar_game=True, macrons=macrons)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'giveup'):
            if author in self.players_to_game_owners:
                game_owner = self.players_to_game_owners[author]
                game = self.games[game_owner]
                game.end_player_sess(author)
                if game.is_word_game:
                    formatted = game.answer.split('/')[-1]
                elif game.is_grammar_game:
                    formatted = game.answer
                else:
                    formatted = self.robot.format_name(game.answer)
                del self.players_to_game_owners[author]
                if game.no_players_left():
                    await channel.send(
                        f"{author.mention} has left the game. There are no players left. The answer was {formatted}.")
                    self.end_game(game_owner)
                else:
                    await channel.send(f"{author.mention} has left the game.")
            return

        # ==================================================================================================================================================

        if author in self.players_to_game_owners:
            game_owner = self.players_to_game_owners[author]
            game = self.games[game_owner]
            response_content = content.lower().strip()
            if game.game_on and response_content in self.authors_set and channel == game.channel:
                if game.players_dict[author].game_on and game.players_dict[author].tries < MAX_TRIES:
                    await self.process_guess(channel, author, content)
            elif game.game_on and channel == game.channel and response_content.startswith(
                    'g ') or response_content.startswith('guess '):
                args = shlex.split(response_content)
                if len(args) < 2:
                    await channel.send("Please guess a word.")
                    return
                else:
                    guess = ' '.join(args[1:])
                    if game.players_dict[author].game_on and game.players_dict[author].tries < MAX_TRIES:
                        if game.is_word_game:
                            await self.process_guess(channel, author, guess, True)
                        else:
                            await self.process_guess(channel, author, guess, False)
                return
            return

            # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'join'):
            args = shlex.split(content.lower())
            if len(args) < 2:
                return

            if args[0] != 'join':
                return

            if '@' not in args[1]:
                return

            if len(message.mentions) > 0:
                game_owner = message.mentions[0]
                if game_owner == author:
                    await channel.send("You cannot join your own game!")
                    return
                if game_owner not in self.games:
                    await channel.send(f"{author.mention}, that person does not have a running game.")
                    return
                if self.games[game_owner].game_on:
                    if author in self.games[game_owner].exited_players:
                        await channel.send("You cannot rejoin a game that you've exited")
                        return
                    self.players_to_game_owners[author] = game_owner
                    self.games[game_owner].add_player(author)
                    await channel.send(f"{author.mention} has joined the game started by {game_owner.mention}.")
                else:
                    channel.send(f"{author.mention}, you attempted to join a game that doesn't exist.")
            else:
                await channel.send(
                    f"{author.mention}, please specify the name of the player whose game you want to join.")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'getshuowen'):
            args = shlex.split(content)
            if len(args) > 1:
                c = args[1]
                explanation = self.robot.get_shuowen_char_etymology(c)
                await channel.send(explanation)
            else:
                await channel.send("You did not enter a character.")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'lookup'):
            args = shlex.split(content)
            source = args[1]
            char = args[2]
            if source == 'wikt':
                await channel.send(lookup_wikt.combine_outputs(char))
            return

        if content.lower().startswith(self.command_prefix + 'give me a toga'):
            latin_guild = self.get_guild(LATIN_SERVER_ID)
            togam_gerens_role = discord.utils.get(latin_guild.roles, id=TOGAM_GERENS_ROLE)
            await author.add_roles(togam_gerens_role, atomic=True)
            await channel.send(f"{author.mention} now has the Togam gerens role. Congrats.")

        if content.lower().startswith(self.command_prefix + 'guildcount') and author.id == 285179803819311106:
            await channel.send(f"This bot is in {len(self.guilds)} servers")
            guilds_list = '\n'.join(self.guilds)
            await channel.send(f"The servers are: {guilds_list}")
