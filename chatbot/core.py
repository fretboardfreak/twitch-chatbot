"""The core twich chatbot logic."""

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

import logging

from twitchio.ext import commands


class Bot(commands.Bot):
    """The core twitch chatbot object."""

    default_command_prefix = '?'

    def __init__(self, token, channels):
        """Initialize the bot object."""
        super().__init__(token=token, prefix=self.default_command_prefix, initial_channels=channels)

    async def event_ready(self):
        """Notify console when bot is logged in and ready to chat and use commands."""
        logging.info(f'Logged in as | {self.nick}')
        logging.debug(f'User id is | {self.user_id}')

    async def event_message(self, message):
        """Watch every message sent in the joined chats."""
        if message.echo:  # Messages with echo set to True are messages sent by the bot.
            return

        logging.info(message.content)

        await self.handle_commands(message)

    @commands.command()
    async def hello(self, ctx: commands.Context):
        """Test command, "hello" to show the bot is working."""
        await ctx.send(f'Hello {ctx.author.name}!')
