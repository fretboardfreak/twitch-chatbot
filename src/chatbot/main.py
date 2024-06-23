"""Main logic for running the twitch chatbot."""

# Copyright 2024 Curtis Sand
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import logging

from . import core
from . import token
from .wordgame import Wordgame
from .pokemon import Pokedex

from .version import __version__


def main():
    """Execute the logic for CLI scripts to run the twitch chatbot."""
    logging.basicConfig(format='[%(levelname)s] %(asctime)s - %(module)s %(funcName)s: %(message)s',
                        level=logging.WARNING)

    args = parse_cli()
    access_token = token.get_access_token(args.token)
    bot = core.Bot(token=access_token, channels=args.channels, moderators=args.mods)

    if args.wordgame:
        bot.add_cog(Wordgame(bot, description=args.summary, wordlist_yaml_file=args.wordlist))

    if args.pokemon:
        bot.add_cog(Pokedex())

    bot.run()


def parse_cli():
    """Parse the CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', help='Print the version and exit.', action='version',
                        version=f'%(prog)s {__version__}')
    DebugAction.add_parser_argument(parser)
    VerboseAction.add_parser_argument(parser)

    parser.add_argument('-t', '--token', type=argparse.FileType('r'), default=None,
                        help='The Twitch API OAuth2 token for the user account the bot will use.')
    parser.add_argument('-c', '--channel', action='append', dest='channels',
                        help='A channel for this bot to join')
    parser.add_argument('-m', '--moderator', action='append', dest='mods',
                        help='A twitch user that is a mod for this bot')

    # wordgame options
    parser.add_argument('-w', '--wordgame', help="Activate the wordgame chatbot commands.",
                        action='store_true', default=False)
    parser.add_argument('-s', '--summary', dest='summary', default=None,
                        help="A short description of the wordgame to activate. i.e. describe the wordlist.")
    parser.add_argument('-l', '--wordlist', type=argparse.FileType('r'), default=None,
                        help='A yaml file containing a named collection of word lists.')

    # pokemon options
    parser.add_argument('-p', '--pokemon', help="Activate the pokedex command.",
                        action='store_true', default=False)

    return parser.parse_args()


class DebugAction(argparse.Action):
    """Enable the debugging output mechanism."""

    sflag = '-d'
    flag = '--debug'
    help = 'Enable debugging output.'

    @classmethod
    def add_parser_argument(cls, parser):
        """Add this argument to the parser."""
        parser.add_argument(cls.sflag, cls.flag, help=cls.help, action=cls)

    def __init__(self, option_strings, dest, **kwargs):
        """Initialize the Action."""
        super().__init__(option_strings, dest, nargs=0, default=False, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Set logging level to debug."""
        setattr(namespace, self.dest, True)
        logging.getLogger().setLevel(logging.DEBUG)


class VerboseAction(DebugAction):
    """Enable the verbose output mechanism."""

    sflag = '-v'
    flag = '--verbose'
    help = 'Enable verbose output.'

    def __call__(self, parser, namespace, values, option_string=None):
        """Set logging level to verbose."""
        setattr(namespace, self.dest, True)
        # don't override debug if root_logger.level is < logging.INFO
        root_logger = logging.getLogger()
        if root_logger.level >= logging.INFO:
            root_logger.setLevel(logging.INFO)
