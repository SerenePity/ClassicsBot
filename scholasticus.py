from discord.ext import commands
import discord
import romanize3
import re
import transliteration.greek
import transliteration.hebrew
import transliteration.coptic
import transliteration.middle_chinese
import transliteration.mandarin
import transliteration.korean
from transliterate import translit, get_available_language_codes
import traceback
import random
import time
import robotic_roman
import shlex
from TextToOwO import owo
import my_wiktionary_parser
from robotic_roman import RoboticRoman
from robotic_roman import QuoteContext
import praw

MAX_TRIES = 5
BOT_OWNER = '285179803819311106'
robot = RoboticRoman("")
DISCORD_CHAR_LIMIT = 2000

class PlayerSession():

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


class Game():

    def __init__(self, game_owner, answer, language, channel, is_word_game=False, is_grammar_game=False, word_language='latin'):
        self.game_owner = game_owner
        self.game_on = True
        self.players_dict = dict()
        self.language = language
        self.channel = channel
        self.answer = answer
        self.exited_players = set()
        self.is_word_game = is_word_game
        self.is_grammar_game = is_grammar_game
        self.word_language = word_language
        self.players_dict[game_owner] = PlayerSession(game_owner, answer, language, channel)

    def get_game_owner_sess(self):
        return self.players_dict[self.game_owner]

    def add_player(self, player):
        self.players_dict[player] = PlayerSession(player, self.answer, self.language, self.channel)

    def get_player_sess(self, player):
        return self.players_dict[player]

    def end_player_sess(self, player):
        self.exited_players.add(player)
        if player in self.players_dict:
            self.players_dict[player].end_game()
        del self.players_dict[player]

    def no_players_left(self):
        return all(not self.players_dict[player].game_on for player in self.players_dict)

    def end_game(self):
        self.language = None
        self.word_language = None
        self.answer = None
        self.game_on = False
        self.channel = None
        self.is_word_game = False
        self.exited_players = set()
        self.players_dict = dict()

class Scholasticus(commands.Bot):

    def __init__(self, prefix):
        super().__init__(command_prefix=prefix)
        self.robot = robot
        self.quotes_commands = dict()
        self.markov_commands = dict()
        self.authors = set()
        self.games = dict()
        self.players_to_game_owners = dict()
        self.quote_requestors = dict()
        self.command_dict = dict()

    def sleep_for_n_seconds(self, n):
        time.sleep(n - ((time.time() - self.start_time) % n))

    async def on_ready(self):
        print('Logged on as', self.user)
        await self.change_presence(game=discord.Game(name=self.command_prefix + "helpme for help"))
        self.robot.load_all_models()
        self.authors_set = set()
        for authors in self.robot.authors_collection:
            for author in authors:
                self.authors_set.add(author)

        self.authors_set.add('reddit')
        self.authors = [self.robot.format_name(person) for person in self.authors_set]
        for author in self.authors_set:
            self.markov_commands[f"as {author.lower()} allegedly said:"] = author
            self.quotes_commands[f"as {author.lower()} said:"] = author
        print('Done initializing')

    def sanitize_user_input(self, text):
        return text.replace(',', '').replace('!', '').replace(':','').replace(';', '')

    async def process_guess(self, channel, player, content, word_game=False):

        try:
            if not word_game:
                guess = content.lower().strip()
            else:
                guess = content.strip()
        except:
            await self.send_message(channel, "You forgot to guess an answer.")
            return
        if guess.strip() == "":
            await self.send_message(channel, "You forgot to guess an answer.")
            return
        print("Guess: " + guess)
        game_owner = self.players_to_game_owners[player]
        game_answer = self.games[game_owner].answer.strip()
        print(f"Is wordgame {word_game}")
        print(f"Is grammargame {self.games[game_owner].is_grammar_game}")
        formatted_answer = self.robot.format_name(game_answer) if not (word_game or self.games[game_owner].is_grammar_game) else game_answer.split('/')[-1]
        if guess.lower() == game_answer.lower().split('/')[-1]:
            await self.send_message(channel,
                                    f"{player.mention}, correct! The answer is {formatted_answer}.")
            self.games[game_owner].end_game()
            return
        if self.games[game_owner].language in ['greek', 'latin']:

            if self.games[game_owner].language == 'greek' and guess not in self.robot.greek_authors:
                await self.send_message(channel, "You're playing a Greek game, but picked a Latin author! Try again.")
                return
            if self.games[game_owner].language == 'latin' and guess not in self.robot.latin_authors:
                await self.send_message(channel, "You're playing a Latin game, but picked a Greek author! Try again.")
                return

        self.games[game_owner].get_player_sess(player).tries += 1

        if self.games[game_owner].players_dict[player].tries < MAX_TRIES:
            guesses_remaining = MAX_TRIES - self.games[game_owner].players_dict[player].tries
            if guess.strip().lower() == "hint" and self.games[game_owner].is_word_game:
                etymology = self.robot.get_word_etymology(game_answer, self.games[game_owner].word_language).strip()
                await self.send_message(channel,
                                        f"{player.mention}, you've sacrificed a guess to get the following etymology of the word:\n\n{etymology}\n\nYou now have have {guesses_remaining} {'guesses' if guesses_remaining > 1 else 'guess'} left.")
            elif not self.games[game_owner].is_word_game and guess.strip().lower() == "hint":
                await self.send_message(channel, "No hints.")
            else:
                await self.send_message(channel, f"Wrong answer, {player.mention}, you have {guesses_remaining} {'guesses' if guesses_remaining > 1 else 'guess'} left.")
        else:
            self.games[game_owner].players_dict[player].end_game()
            if self.games[game_owner].no_players_left():
                if len(self.games[game_owner].players_dict) == 1:
                    await self.send_message(channel,
                                    f"Sorry, {player.mention}, you've run out of guesses. The answer was {formatted_answer}. Better luck next time!")
                else:
                    await self.send_message(channel,
                                      f"Everybody has run out of guesses. The answer was {formatted_answer}. Better luck next time!")
                self.end_game(game_owner)
                #self.games[game_owner].end_game()
            else:
                await self.send_message(channel,
                                        f"Sorry, {player.mention}, you've run out of guesses! Better luck next time!")
                self.games[game_owner].get_player_sess(player).end_game()
                self.games[game_owner].exited_players.add(player)
                del self.players_to_game_owners[player]


    async def start_game(self, channel, game_owner, text_set, language='latin', word_language='latin', macrons=True):

        repeat_text = ""
        is_grammar_game = False
        grammar_game_set = []
        is_word_game = False
        #print(text_set)
        text_set = text_set.split('[')[0].strip()
        if game_owner in self.games and self.games[game_owner].game_on:
            repeat_text = "Okay, restarting game. "
        if text_set == "ancientgreek":
            answer = random.choice(self.robot.greek_authors)
        elif text_set == "nomacrongrammar":
            grammar_game_set = my_wiktionary_parser.get_latin_grammar_forms(no_macrons=True)
            answer = grammar_game_set[0]
            passage = "Name the " + random.choice(grammar_game_set[1]).strip()
        elif text_set == "grammar":
            grammar_game_set = my_wiktionary_parser.get_latin_grammar_forms()
            answer = grammar_game_set[0]
            passage = "Name the " + random.choice(grammar_game_set[1]).strip()
        elif text_set == "greekgrammar":
            grammar_game_set = my_wiktionary_parser.get_greek_grammar_forms()
            answer = grammar_game_set[0]
            passage = "Name the " + random.choice(grammar_game_set[1]).strip()
        elif text_set == "word":
            if "-l " in word_language:
                word_language = word_language.replace("-l ", "")
            answer = self.robot.get_random_word(word_language).strip()
            if answer == "Could not find lemma.":
                await self.send_message(channel, "Could not find an entry with an etymology. Please try again.")
                return
            is_word_game = True
        elif text_set == 'latin':
            answer = random.choice(self.robot.latin_authors)
        else:
            print("In other lang")
            grammar_game_set = my_wiktionary_parser.get_grammar_question(text_set)
            answer = grammar_game_set[0]
            passage = "Name the " + random.choice(grammar_game_set[1]).strip()
            if not macrons:
                answer = my_wiktionary_parser.remove_macrons(answer)
            text_set = "otherlang"

        if text_set not in ['word', 'grammar', 'greekgrammar', 'nomacrongrammar', 'otherlang']:
            i, passage, _ = self.robot.random_quote(answer)
        elif text_set in ['grammar', 'greekgrammar', 'nomacrongrammar', 'otherlang']:
            is_grammar_game = True
            to_lower = lambda s: s[:1].lower() + s[1:] if s else ''
            passage = "name the " + to_lower(random.choice(grammar_game_set[1]).strip())
        else:
            passage = self.robot.get_and_format_word_defs(answer, word_language, include_examples=False)
        self.games[game_owner] = Game(game_owner, answer, text_set, channel, is_word_game, is_grammar_game, word_language=word_language)
        self.players_to_game_owners[game_owner] = game_owner
        print("Answer: " + answer)
        if text_set not in ["word", "grammar", "greekgrammar", "nomacrongrammar", "otherlang"]:
            await self.send_message(channel, f"{repeat_text}{game_owner.mention}, name the author or source of the following passage:\n\n_{passage}_")
        elif text_set == 'grammar':
            await self.send_message(channel, f"{repeat_text}{game_owner.mention}, {passage} (note: macrons needed).")
        elif text_set == 'greekgrammar' or text_set == 'nomacrongrammar' or text_set == 'otherlang':
            await self.send_message(channel, f"{repeat_text}{game_owner.mention}, {passage.capitalize()}.")
        else:
            await self.send_message(channel, f"{repeat_text}{game_owner.mention}, state the {word_language.title()} word (in lemma form) with the following definitions:\n\n{passage}")


    def end_game(self, game_owner):
        game = self.games[game_owner]
        for player in game.players_dict:
            if player in self.players_to_game_owners:
                del self.players_to_game_owners[player]
        del self.games[game_owner]

    def is_int(self, n):
        try:
            n = int(n)
            return True
        except:
            False

    async def send_in_chunks_if_needed(self, channel, text, n=2000):
        if len(text) > DISCORD_CHAR_LIMIT:
            chunks = RoboticRoman.chunks(text, n)
            for chunk in chunks:
                await self.send_message(channel, chunk)
        else:
            await self.send_message(channel, text)

    def format_chapter_for_gibbon(self, chapter):
        if "chapter" not in chapter and chapter.lower() != "preface":
            chapter_number = re.findall(r"[0-9]+", chapter)
            if len(chapter_number) > 0:
                chapter = f"Chapter {chapter_number[0]}"
                return chapter
        else:
            return chapter.title()

    def debug(self, channel, content):
        print(f"Channel: {channel.id}")
        print(content)

    async def on_message(self, message):
        # potential for infinite loop if bot responds to itself
        if message.author == self.user:
            return

        author = message.author
        channel = message.channel
        content = message.content

        if content.lower().startswith(self.command_prefix) and content.lower().split()[0].endswith('_def'):
            self.debug(channel, content)
            args = shlex.split(content.replace('“','"').replace('”','"').strip())
            print(args)
            try:
                if len(args) > 1:
                    language = re.search("([(\w_\-)]+)_def", args[0].lower()).group(1).replace('_', ' ')
                    word = ' '.join(args[1:])
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    if not language:
                        language = 'latin'
                    definition = self.robot.get_and_format_word_defs(word, language)
                elif len(args) > 1:
                    word = ' '.join(args[1:])
                    definition = self.robot.get_and_format_word_defs(word)
                else:
                    definition = "Invalid arguments"
                await self.send_in_chunks_if_needed(channel, definition)
                return
            except discord.errors.HTTPException:
                traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await self.send_message(channel, f"The entry is too long. Here's the URL instead: {url}")
            except:
                traceback.print_exc()
                await self.send_message(channel, "An error occurred while trying to retrieve the definition.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'randword') or content.lower().startswith(self.command_prefix + 'randomword'):
            args = shlex.split(content.replace('“','"').replace('”','"').strip())
            language = ""
            self.debug(channel, content)
            try:

                if len(args) == 1:
                    word = self.robot.get_random_word('latin')
                    await self.send_in_chunks_if_needed(channel, self.robot.get_full_entry(word, 'latin'))
                    return
                elif len(args) > 1:
                    language = ' '.join(args[1:])
                    word = self.robot.get_random_word(language)
                    print("SCHOLASTICUS WORD: " + word)
                    print("SCHOLASTICUS WORD: " + language)
                    entry = self.robot.get_full_entry(word, language)
                    await self.send_in_chunks_if_needed(channel, entry)
                    return
            except discord.errors.HTTPException:
                traceback.print_exc()
                if 'proto-' in language.lower():
                    url = f"https://en.wiktionary.org/wiki/{word}"
                else:
                    url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await self.send_message(channel, f"The entry is too long. Here's the URL instead: {url}")
            except:
                traceback.print_exc()
                await self.send_message(channel, "An error occurred while trying to retrieve the word.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix) and content.split()[0].lower().endswith('_ety'):
            args = shlex.split(content.replace('“','"').replace('”','"').strip())
            self.debug(channel, content)
            try:
                if len(args) > 1:
                    language = re.search("([\w_\-]+)_ety", args[0].lower()).group(1).replace('_', ' ')
                    word = ' '.join(args[1:])
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    if not language:
                        language = 'latin'
                    etymology = self.robot.get_word_etymology(word, language)
                elif len(args) > 1:
                    word = ' '.join(args[1:])
                    etymology = self.robot.get_word_etymology(word)
                else:
                    etymology = "Invalid arguments"
                await self.send_in_chunks_if_needed(channel, etymology)
                return
            except discord.errors.HTTPException:
                traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await self.send_message(channel, f"The entry is too long. Here's the URL instead: {url}")
            except:
                traceback.print_exc()
                await self.send_message(channel, "An error occurred while trying to retrieve the etymology.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix) and content.split()[0].lower().endswith('_word'):
            args = shlex.split(content.replace('“','"').replace('”','"').strip())
            self.debug(channel, content)
            try:
                if len(args) > 1:
                    language = re.search("([\w_\-]+?)_word", args[0].replace(':','').lower()).group(1).replace('_', ' ')
                    if not language:
                        language ='latin'
                    word = ' '.join(args[1:])
                    print("Language: " + language)
                    print("word: " + word)
                    if 'proto-' in language:
                        word = self.robot.format_reconstructed(language, word)
                    entry = self.robot.get_full_entry(word, language)
                elif len(args) > 1:
                    word = ' '.join(args[1:])
                    entry = self.robot.get_full_entry(word)
                else:
                    entry = "Invalid arguments"
                await self.send_in_chunks_if_needed(channel, entry)
                return
            except discord.errors.HTTPException:
                traceback.print_exc()
                url = f"https://en.wiktionary.org/wiki/{word}#{language.title()}"
                await self.send_message(channel, f"The entry is too long. Here's the URL instead: {url}")
            except:
                traceback.print_exc()
                await self.send_message(channel, "An error occurred while trying to retrieve the word entry.")
                return

        if content.lower().startswith(self.command_prefix + 'listparallel'):
            self.debug(channel, content)
            parallel_list = '\n'.join(self.robot.parallel_authors)
            await self.send_message(channel, parallel_list)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'latin_grammar'):
            self.debug(channel, content)
            if "-m" in content.lower():
                macrons = True
            else:
                macrons = False
            if not macrons:
                await self.start_game(channel, author, "nomacrongrammar", "latin", None)
            else:
                await self.start_game(channel, author, "grammar", "latin", None)
            return

        if content.lower().startswith(self.command_prefix + 'ancient_greek_grammar'):
            await self.start_game(channel, author, "greekgrammar", "greek", None)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'parallel'):
            self.debug(channel, content)
            args = shlex.split(content.lower().strip())
            last_arg = args[-1].strip()
            #print("last_arg " + last_arg)
            try:
                if self.is_int(last_arg):
                    #print("Matched num")
                    person = ' '.join(args[1:-1])
                    #print("PERSON: " + person)
                    await self.send_message(channel, self.robot.get_parallel_quote(person, int(last_arg) - 1))
                    return
                else:
                    person = ' '.join(args[1:])
                    await self.send_message(channel, self.robot.get_parallel_quote(person))
                    return
            except:
                traceback.print_exc()
                await self.send_message(channel, "Error. I do not have parallel texts for this person.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'redditquote'):
            self.debug(channel, content)
            try:
                subreddit = shlex.split(content.lower().strip())[1]
                await self.send_in_chunks_if_needed(channel, self.robot.reddit_quote(subreddit))
            except:
                traceback.print_exc()
                await self.send_message(channel, "Error. Subreddit possibly doesn't exist.")

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'bibleversions'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if len(args) > 1:
                language = ' '.join(args[1:]).lower()
                print(language)
                ret_list = self.robot.get_available_bible_versions_lang(language)
                try:
                    for version in ret_list:
                        await self.send_message(channel, version)
                except discord.errors.HTTPException:
                    traceback.print_exc()
                    await self.send_message(channel, f"The entry is too long. Here's the URL instead: {url}")
                except:
                    traceback.print_exc()
                    await self.send_message(channel, "Invalid language. Type '>bibleversions' for get available versions for all languages.")
            else:
                try:
                    await self.send_message(channel, self.robot.get_available_bible_versions())
                except discord.errors.HTTPException:
                    traceback.print_exc()
                    await self.send_message(channel, f"Text is too long.")

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'tr '):
            self.debug(channel, content)
            try:
                tr_args = shlex.split(content)
            except:
                await self.send_message(channel, "Error, no closing quotation. Please try to enclose the input within quotes.")
                return
            if len(tr_args) > 2:
                language = tr_args[1].lower()
            else:
                await self.send_message(channel, "Invalid arguments.")
            try:
                input = ' '.join(tr_args[2:])
                if language == '-heb':
                    transliterated = transliteration.hebrew.transliterate(input)
                elif language == '-cop':
                    transliterated = transliteration.coptic.transliterate(input)
                elif language == '-unc':
                    transliterated = transliteration.latin_antique.transliterate(input)
                elif language == '-mc':
                    transliterated = transliteration.middle_chinese.transliterate(input)
                elif language == '-mand':
                    transliterated = transliteration.mandarin.transliterate(input)
                elif language == '-aram':
                    r = romanize3.__dict__['arm']
                    transliterated = r.convert(input)
                elif language == '-arab':
                    r = romanize3.__dict__['ara']
                    transliterated = r.convert(input)
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
                else:
                    transliterated = transliteration.greek.transliterate(input)
                await self.send_message(channel, transliterated)
                return
            except Exception as e:
                traceback.print_exc()
                await self.send_message(channel, f"Error transliterating input.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'textend') or content.lower().startswith(self.command_prefix + 'txend'):
            self.debug(channel, content)
            qt_obj = self.quote_requestors[author]
            del qt_obj
            self.quote_requestors[author] = None

        # ==================================================================================================================================================

        def process_gibbon_footnots(self, file):
            self.debug(channel, content)
            return [q.rstrip('\n') for q in file.read().split(robotic_roman.ABSOLUTE_DELIMITER)]

        if content.lower().startswith(self.command_prefix + 'pick'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if not args[0].lower() == 'pick':
                return
            if len(args) < 2:
                await self.send_message(channel, "You need to pick an index.")
                return
            index = 0
            qt_obj: QuoteContext = self.quote_requestors[author]
            source = qt_obj.author

            try:
                index = int(args[1])
            except:
                self.send_message(channel, "Index must be an integer.")
                return
            if source.lower().strip() == 'gibbon':
                module = qt_obj.works_list[index - 1]
                if 'footnotes' in module.__file__:
                    quotes = []
                    for chapter in module.footnotes:
                        quotes += [fn + '\n\n' for fn in module.footnotes[chapter]]
                    qt_obj.works_list[index - 1] = module
                    qt_obj.quotes = quotes
                    qt_obj.index = 0
                    qt_obj.after_index = 0
                    qt_obj.author = 'gibbon'
                    await self.send_message(channel, qt_obj.get_surrounding(after=1, joiner=""))
                else:
                    quotes = module.quotes
                    qt_obj.works_list[index - 1] = module
                    qt_obj.quotes = quotes
                    qt_obj.index = 0
                    qt_obj.after_index = 0
                    qt_obj.author = 'gibbon'
                    await self.send_message(channel, qt_obj.get_surrounding(after=1))
                return

            file = qt_obj.works_list[index - 1]
            if file.closed:
                qt_obj.works_list[index - 1] = open(file.name)
                file = qt_obj.works_list[index - 1]
            file.seek(0)
            if source == 'the bible':
                quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_holy_text)
            elif source.lower() == "joyce":
                quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_basic)
            elif source.lower() == "bush" or source.lower() == "yogi berra":
                quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_absolute)
            elif source.lower() == "jaspers":
                quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_basic)
            elif source.lower() == "gibbon" and 'footnotes' in file.name:
                quotes = [q.rstrip('\n') for q in file.read().split(robotic_roman.ABSOLUTE_DELIMITER)]
            elif source.lower() == "mommsen":
                if 'contents' in file.name:
                    print("In contents")
                    quotes = self.robot.get_passage_list_for_file(file, lambda x: [x])
                    await self.send_message(channel, quotes[0])
                    return
                else:
                    quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_text)
            else:
                quotes = self.robot.get_passage_list_for_file(file, RoboticRoman._process_text)
            qt_obj = QuoteContext(source, quotes, 0, works_list=qt_obj.works_list)
            self.quote_requestors[author] = qt_obj
            try:
                await self.send_message(channel, qt_obj.get_surrounding(after=1))
            except:
                display, workslist = self.robot.show_author_works(source)
                print("WORKSLIST:")
                print(workslist)
                if workslist[index-1].name == 'modern_historians/gibbon/footnotes_from_gibbon.txt':
                    qt_obj = QuoteContext(source,
                                          [ q.rstrip('\n') for q in
                                            RoboticRoman._process_absolute(open(workslist[index - 1].name, encoding='utf8').read())
                                          ], 0, workslist)
                else:
                    qt_obj = QuoteContext(source, RoboticRoman._process_text(open(workslist[index - 1].name, encoding='utf8').read()), 0, workslist)
                self.quote_requestors[author] = qt_obj
                await self.send_message(channel, qt_obj.get_surrounding(after=1))
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'textstart') or content.lower().startswith(self.command_prefix + 'tstart'):
            args = shlex.split(content.lower())
            self.debug(channel, content)
            if len(args) < 2:
                await self.send_message(channel, "You must provide an author or work.")
            else:
                source = ' '.join(args[1:])
                if source not in self.authors_set:
                    source = "the " + source.strip().lower()
                display, workslist = self.robot.show_author_works(source)
                print("Display: " + str(display))
                print("Workslist: " + str(workslist))
                qt_obj = QuoteContext(source, [], 0, workslist)
                self.quote_requestors[author] = qt_obj
                if len(display) > 2000:
                    parts = list(RoboticRoman.chunks(display.split('\n'), 10))
                    for part in parts:
                        await self.send_message(channel, ' '.join(part))
                else:
                    await self.send_message(channel, display)

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'ulfilas'):
            self.debug(channel, content)
            qt_args = shlex.split(content)
            print(qt_args)
            try:
                if len(qt_args) > 1:
                    version = qt_args[1]
                else:
                    version = 'kjv'
                translation = self.robot.ulfilas_translations(version)
                await self.send_message(channel ,translation)

            except Exception as e:
                traceback.print_exc()
                await self.send_message(channel, "Error retrieving verse.")

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'biblecompare'):
            self.debug(channel, content)
            qt_args = shlex.split(content)
            print(qt_args)
            try:
                if len(qt_args) > 4 and self.is_int(qt_args[1]):
                    verse = ' '.join([qt_args[1], qt_args[2], qt_args[3]])
                    versions = qt_args[4:]
                    translation = self.robot.bible_compare(verse, versions)
                elif len(qt_args) > 2 and re.match(r"[0-9]+:[0-9]+", qt_args[2]):
                    verse = qt_args[1] + ' ' + qt_args[2]
                    print("Verse: " + verse)
                    versions = qt_args[3:]
                    translation = self.robot.bible_compare(verse, versions)
                elif len(qt_args) > 1:
                    versions = qt_args[1:]
                    translation = self.robot.bible_compare_random_verses(versions)
                else:
                    await self.send_message(channel, "Invalid arguments.")
                    return
                await self.send_message(channel ,translation)
                return
            except discord.errors.HTTPException:
                traceback.print_exc()
                await self.send_message(channel, f"Text is too long.")
            except Exception as e:
                traceback.print_exc()
                await self.send_message(channel, "Verse not found. Please check that you have a valid Bible version by checking here https://www.biblegateway.com/versions, and here https://getbible.net/api.")
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'qt') or content.lower().strip() in self.quotes_commands:
            if content.lower().startswith("as") and content.lower().endswith("said:"):
                source = self.quotes_commands[content.lower().strip()]
                index, quote, quotes_list = self.robot.random_quote(source.lower(), None, False,
                                                                    case_sensitive=False)
                quote = re.sub(r"([?!])\s*\.", r"\1", quote)
                _, works_list = self.robot.show_author_works(source)
                qt_obj = QuoteContext(source.lower(), quotes_list, index + 1, works_list=works_list)
                self.quote_requestors[author] = qt_obj
                await self.send_message(channel, quote)
            else:
                self.debug(channel, content)
                qt_args = shlex.split(content.replace('“','"').replace('”','"'))
                if qt_args[0].lower() != 'qt':
                    return
                print(qt_args)
                word = None
                transliterate = False
                lemmatize = False
                case_sensitive = False
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
                        source = ' '.join(qt_args[4:]).lower().strip()
                    elif word and not transliterate:
                        source = ' '.join(qt_args[3:]).lower().strip()
                    elif transliterate and not word:
                        source = ' '.join(qt_args[2:]).lower().strip()
                    elif not word and not transliterate:
                        source = ' '.join(qt_args[1:]).lower().strip()
                    if word:
                        word = self.sanitize_user_input(word)

                    if source not in self.authors_set:
                        source = "the " + source.strip().lower()

                    if transliterate:
                        if source == "reddit":
                            subreddit = self.robot.reddit.random_subreddit(nsfw=False)
                            await self.send_in_chunks_if_needed(channel,
                                                    f"From r/{subreddit.display_name}:\n{robot.reddit_quote(subreddit.display_name)}")
                            return
                        index, quote, quotes_list = self.robot.random_quote(source.lower(), word, lemmatize, case_sensitive=case_sensitive)
                        _, works_list = self.robot.show_author_works(source)
                        qt_obj = QuoteContext(source.lower(), quotes_list, index + 1, works_list)
                        self.quote_requestors[author] = qt_obj
                        transliterated = transliteration.greek.transliterate(quote)
                        await self.send_message(channel, transliterated)
                        return
                    else:
                        if source == "reddit":
                            subreddit = self.robot.reddit.random_subreddit(nsfw=False)
                            print(subreddit.display_name)
                            await self.send_in_chunks_if_needed(channel, f"From r/{subreddit.display_name}:\n{robot.reddit_quote(subreddit.display_name)}")
                            return
                        index, quote, quotes_list = self.robot.random_quote(source.lower(), word, lemmatize, case_sensitive=case_sensitive)
                        quote = re.sub(r"([?!])\s*\.", r"\1", quote)
                        _, works_list = self.robot.show_author_works(source)
                        qt_obj = QuoteContext(source.lower(), quotes_list, index + 1, works_list=works_list)
                        self.quote_requestors[author] = qt_obj
                        await self.send_message(channel, quote)
                except discord.errors.HTTPException:
                    traceback.print_exc()
                    await self.send_message(channel, f"The passage is too long.")
                except Exception as e:
                    traceback.print_exc()
                    if not source:
                        await self.send_message(channel, "No person provided")
                    else:
                        await self.send_message(channel, f"Could not find quotes matching criteria.")
                return

        # ==================================================================================================================================================

        if content.lower().strip() == self.command_prefix + "whatchapter":
            self.debug(channel, content)
            print("In whatchapter")
            try:
                qt_obj: QuoteContext = self.quote_requestors[author]
            except:
                await self.send_message(channel, "You have not started reading anything yet.")
                return
            if qt_obj.author != "gibbon":
                await self.send_message(channel, f"This utility if only for finding which chapter of Gibbon's Decline and Fall you are reading.")
                return
            chapter = qt_obj.find_chapter_from_passage()
            if chapter == "Preface":
                await self.send_message(channel, f"You are in the Preface in Volume 1")
            else:
                await self.send_message(channel, f"You are in {chapter}")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'fn'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if args[0].lower() != 'fn':
                return
            if len(args) == 2:
                try:
                    qt_obj: QuoteContext = self.quote_requestors[author]
                except:
                    await self.send_message("The current command form assumes that you are reading Gibbon and are trying to retrieve a footnote from a passage you have just read, but htis does not appear to be the case.")
                    return
                chapter = qt_obj.find_chapter_from_passage()
                try:
                    footnote_num = int(args[1])
                except:
                    await self.send_message(channel, "Footnote number must be an integer.")
                    return
                footnote = self.robot.get_gibbon_footnote(chapter, footnote_num)
                await self.send_in_chunks_if_needed(channel, footnote)
                return
            if len(args) == 3:
                chapter = args[1].title()
                chapter = self.format_chapter_for_gibbon(chapter)
                try:
                    footnote_num = int(args[2])
                except:
                    await self.send_message(channel, "Footnote number must be an integer.")
                    return
                footnote = self.robot.get_gibbon_footnote(chapter, footnote_num)
                await self.send_in_chunks_if_needed(channel, footnote)
            elif len(args) == 4:
                chapter = args[1].title()
                chapter = self.format_chapter_for_gibbon(chapter)
                try:
                    footnote_num = int(args[2])
                except:
                    await self.send_message(channel, "Footnote number must be an integer.")
                    return
                try:
                    footnote_end = int(args[3])
                except:
                    await self.send_message(channel, "Footnote number must be an integer.")
                    return
                if footnote_end - footnote_num > 4:
                    await self.send_message(channel, "For the sake of sanity, please retrieve only five footnotes at a time.")
                    return
                footnote = self.robot.get_gibbon_footnote(chapter, footnote_num, footnote_end)
                await self.send_in_chunks_if_needed(channel, footnote)
            else:
                await self.send_message(channel, "Wrong number of arguments. Type helpme for help.")
                return
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'next'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if args[0].lower() != 'next':
                return
            if len(args) < 2:
                after = 1
            else:
                after = int(args[1])
                if after < 1:
                    await self.send_message(channel, f"You must pick a number greater than 0.")
                    return
                if after > 5:
                    await self.send_message(channel, f"You must pick a number less than 6 to remain within Discord's character limit.")
                    return
            try:
                qt_obj: QuoteContext = self.quote_requestors[author]
                if qt_obj.author.lower() in robotic_roman.ABSOLUTE_DELIMITER_AUTHORS:
                    await self.send_in_chunks_if_needed(channel, qt_obj.get_surrounding(after=after, joiner=""))
                elif qt_obj.author.lower() == 'gibbon' and 'footnotes' in qt_obj.find_chapter_from_passage():
                    await self.send_in_chunks_if_needed(channel, qt_obj.get_surrounding(after=after, joiner=""))
                elif qt_obj.author.lower() == 'the bible':
                    await self.send_in_chunks_if_needed(channel, re.sub(r"[\.](\w)", r"\1",
                                                            self.quote_requestors[author].get_surrounding(after=after)))
                else:
                    #print(f"QuotesAtServiceLayer: {self.quote_requestors[author].quotes}")
                    await self.send_in_chunks_if_needed(channel, re.sub(r"([?!])\s*\.", r"\1", self.quote_requestors[author].get_surrounding(after=after)))
            except discord.errors.HTTPException:
                traceback.print_exc()
                await self.send_message(channel, f"Text is too long.")
            return

        if content.lower().startswith(self.command_prefix + 'bef'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if args[0].lower() != 'bef':
                return
            if len(args) < 2:
                before = 1
            else:
                before = int(args[1])
                if before < 1:
                    await self.send_message(channel, f"You must pick a number greater than 0.")
                    return
                if before > 5:
                    await self.send_message(channel, f"You must pick a number less than 6 to remain within Discord's character limit.")
                    return
            try:
                qt_obj: QuoteContext = self.quote_requestors[author]
                if qt_obj.author.lower() in robotic_roman.ABSOLUTE_DELIMITER_AUTHORS:
                    await self.send_in_chunks_if_needed(channel, qt_obj.get_surrounding(before=before, joiner=""))
                elif qt_obj.author.lower() == 'gibbon' and 'footnotes' in qt_obj.find_chapter_from_passage():
                    await self.send_in_chunks_if_needed(channel, qt_obj.get_surrounding(before=before, joiner=""))
                else:
                    await self.send_in_chunks_if_needed(channel, re.sub(r"([?!])\s*\.", r"\1", qt_obj.get_surrounding(before=before)))
            except discord.errors.HTTPException:
                traceback.print_exc()
                await self.send_message(channel, f"Text is too long.")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'surr'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if args[0].lower() != 'surr':
                return
            if len(args) < 3:
                before = 1
                after = 1
            else:
                before = int(args[1])
                after = int(args[2])
            try:
                qt_obj: QuoteContext = self.quote_requestors[author]
                if qt_obj.author.lower() in robotic_roman.ABSOLUTE_DELIMITER_AUTHORS:
                    surr_quotes = qt_obj.get_surrounding(before=before, after=after, joiner="")
                    await self.send_in_chunks_if_needed(channel, surr_quotes)
                elif qt_obj.author.lower() == 'gibbon' and 'footnotes' in qt_obj.find_chapter_from_passage():
                    surr_quotes = qt_obj.get_surrounding(before=before, after=after, joiner="")
                    await self.send_in_chunks_if_needed(channel, surr_quotes)
                elif qt_obj.author.lower() == 'the bible':
                    await self.send_in_chunks_if_needed(channel, re.sub(r"[\.](\w)", r"\1", qt_obj.get_surrounding(before=before, after=after)))
                else:
                    surr_quotes = qt_obj.get_surrounding(before=before, after=after)
                    surr_quotes = re.sub(r"([?!])\s*\.", r"\1", surr_quotes)
                    await self.send_in_chunks_if_needed(channel, surr_quotes)
            except discord.errors.HTTPException:
                traceback.print_exc()
                await self.send_message(channel, f"The passage is too long.")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'owo'):
            self.debug(channel, content)
            qt_args = shlex.split(content.replace('“','"').replace('”','"'))
            print(qt_args)
            try:
                author = ' '.join(qt_args[1:]).lower().strip()
                to_transliterate = False
                if author in self.robot.greek_authors:
                    to_transliterate = True
                quote = self.robot.random_quote(author.lower())[1]
                if to_transliterate:
                    quote = transliteration.greek.transliterate(quote)
                await self.send_message(channel, owo.text_to_owo(quote))
            except Exception as e:
                traceback.print_exc()
                if not author:
                    await self.send_message(channel, "No person provided")
                else:
                    await self.send_message(channel, f"I do not have quotes for {self.robot.format_name(author)}.")

        # ==================================================================================================================================================

        if content.strip().lower().startswith(self.command_prefix + "markov"):
            self.debug(channel, content)
            markov_args = shlex.split(content.replace('“','"').replace('”','"'))
            print(markov_args)
            try:
                if (markov_args[1].strip() == '-t'):
                    author = ' '.join(markov_args[2:]).lower().strip()
                    transliterated = transliteration.greek.transliterate(self.robot.make_sentence(author.lower())).replace(robotic_roman.ABSOLUTE_DELIMITER, "")
                    await self.send_message(channel, transliterated)
                    return
                else:
                    author = ' '.join(markov_args[1:]).strip().lower()
                    await self.send_message(channel, self.robot.make_sentence(author.lower()).replace(robotic_roman.ABSOLUTE_DELIMITER, ""))
                    return
            except Exception as e:
                traceback.print_exc()
                if not author:
                    await self.send_message(channel, "No person provided")
                else:
                    await self.send_message(channel, f"I do not have a Markov model for {self.robot.format_name(author)}.")

        # ==================================================================================================================================================

        if content.strip().lower() in self.markov_commands:
            self.debug(channel, content)
            author = self.markov_commands[content.strip().lower().replace('“','"').replace('”','"')]
            try:
                await self.send_message(channel, self.robot.make_sentence(author.lower()))
            except Exception as e:
                traceback.print_exc()
                if not author:
                    await self.send_message(channel, "No person provided")
                else:
                    await self.send_message(channel, f"I do not have a Markov model for {self.robot.format_name(author)}.")

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'literaturequote'):
            self.debug(channel, content)
            await self.send_message(channel, self.robot.pick_random_literature_quote())

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'historianquote'):
            self.debug(channel, content)
            await self.send_message(channel, self.robot.pick_random_historians_quote())

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'philosopherquote'):
            self.debug(channel, content)
            await self.send_message(channel, self.robot.pick_random_philosopher_quote())

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'germanicquote'):
            self.debug(channel, content)
            await self.send_message(channel, self.robot.pick_random_germanic_quote())

        # ==================================================================================================================================================
        if content.lower().startswith(self.command_prefix + 'latinquote'):
            self.debug(channel, content)
            await self.send_message(channel, self.robot.pick_random_latin_quote())

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'greekquote'):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            transliterate = len(args) > 1 and args[1] == '-t'
            quote = self.robot.pick_greek_quote()
            if transliterate:
                quote = transliteration.greek.transliterate(quote)
            await self.send_message(channel, quote)

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'comm '):
            self.debug(channel, content)
            args = shlex.split(content.lower())
            if len(args) < 2:
                await self.send_message(channel, "No argument provided")
                return
            else:
                try:
                    i = int(args[1])
                except:
                    await self.send_message(channel, "Argument must be an integer.")
                await self.send_message(channel, f"Type {self.command_dict[i]}")

        # ==================================================================================================================================================

        if content.lower().strip() == self.command_prefix + 'helpme':
            self.debug(channel, content)
            help = self.robot.commands
            ret = []
            for i in range(len(help)):
                desc = help[i][0].strip()
                self.command_dict[i+1] = command = help[i][1]
                ret.append(f"**{i+1}.** {desc}")
            lines = list(RoboticRoman.chunks(ret, 5))
            print('Pick the number to see the command:\n' + '\n'.join(ret))
            await self.send_message(channel, 'Enter \'comm <number>\' to see the command:\n' + '\n'.join(['\t'.join(lst) for lst in lines]))

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'germanicauthors'):
            self.debug(channel, content)
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.germanic_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'latinauthors'):
            self.debug(channel, content)
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.latin_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'greekauthors'):
            self.debug(channel, content)
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.greek_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'modernphilosophers'):
            self.debug(channel, content)
            await self.send_message(channel, '```yaml\n' + ', '.join([self.robot.format_name(a) for a in sorted(self.robot.philosophers_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'modernhistorians'):
            self.debug(channel, content)
            await self.send_message(channel, '```yaml\n' + ', '.join(
                [self.robot.format_name(a) for a in sorted(self.robot.historians_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'modernauthors'):
            await self.send_message(channel, '```yaml\n' + ', '.join(
                [self.robot.format_name(a) for a in sorted(self.robot.literature_quotes_dict.keys())]) + '```')

        # ==================================================================================================================================================
        if content.lower().startswith(self.command_prefix + 'greekgame'):
            await self.start_game(channel, author, "ancientgreek")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'latingame'):
            await self.start_game(channel, author, "latin")
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'wordgame'):
            args = shlex.split(content.lower().replace('“','"').replace('”','"'))
            if len(args) > 1:
                language = ' '.join(args[1:]).strip()
            else:
                language = 'latin'
            await self.start_game(channel, author, "word", word_language=language)
            return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'greekgame'):
            await self.start_game(channel, author, "greek")
            return

        # ==================================================================================================================================================

        if content.lower().endswith('_grammar') or content.lower().endswith('_grammar -m'):
            args = shlex.split(content.lower())
            macrons = '-m' in content.lower()
            language = content.lower().split('_grammar')[0].replace('_', ' ')
            await self.start_game(channel, author, language, macrons=macrons)
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
                    await self.send_message(channel, f"{author.mention} has left the game. There are no players left. The answer was {formatted}.")
                    self.end_game(game_owner)
                else:
                    await self.send_message(channel, f"{author.mention} has left the game.")
            return

        # ==================================================================================================================================================

        if author in self.players_to_game_owners :
            game_owner = self.players_to_game_owners[author]
            game = self.games[game_owner]
            response_content = content.lower().strip()
            if game.game_on and response_content in self.authors_set and channel == game.channel:
                if game.players_dict[author].game_on and game.players_dict[author].tries < MAX_TRIES:
                    await self.process_guess(channel, author, content)
            elif game.game_on and channel == game.channel and response_content.startswith('g ') or response_content.startswith('guess '):
                args = shlex.split(response_content)
                if len(args) < 2:
                    await self.send_message(channel, "Please guess a word.")
                    return
                else:
                    guess = ' '.join(args[1:])
                    if game.players_dict[author].game_on and game.players_dict[author].tries < MAX_TRIES:
                        if game.is_word_game:
                            await self.process_guess(channel, author, guess, True)
                        else:
                            await self.process_guess(channel, author, guess, False)
                return

        # ==================================================================================================================================================

        if content.lower().startswith(self.command_prefix + 'join'):
            if len(message.mentions) > 0 :
                game_owner = message.mentions[0]
                if game_owner == author:
                    await self.send_message(channel, "You cannot join your own game!")
                    return
                if game_owner not in self.games:
                    await self.send_message(channel, f"{author.mention}, that person does not have a running game.")
                    return
                if self.games[game_owner].game_on:
                    if author in self.games[game_owner].exited_players:
                        await self.send_message(channel, "You cannot rejoin a game that you've exited")
                        return
                    self.players_to_game_owners[author] = game_owner
                    self.games[game_owner].add_player(author)
                    await self.send_message(channel, f"{author.mention} has joined the game started by {game_owner.mention}.")
                else:
                    self.send_message(channel, f"{author.mention}, you attempted to join a game that doesn't exist.")
            else:
                await self.send_message(channel,
                                        f"{author.mention}, please specify the name of the player whose game you want to join.")
