"""Logic for retrieving and handling the twitch access token."""

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

import os


ENV_VAR = 'TWITCH_ACCESS_TOKEN'


class TokenError(Exception):
    """Exception used to indicate an error with the Token."""


def get_access_token(input_file):
    """Retrieve a twitch user's Oauth2 token."""
    # if input file is valid use that
    if input_file is not None and not input_file.closed:
        return input_file.read().strip()

    if ENV_VAR in os.environ:
        return os.environ[ENV_VAR]

    raise TokenError('Missing Token: The twitch access token must be provided to the chatbot. '
                     'The token must be provided either in an environment variable '
                     '"TWITCH_ACCESS_TOKEN" or in a file in the CWD named "twitch_access_token"')
