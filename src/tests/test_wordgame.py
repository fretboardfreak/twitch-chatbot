"""Tests for the wordgame."""

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

import pytest

import chatbot.wordgame as wordgame


@pytest.fixture
def uncache_wordgame_data():
    wordgame.Wordgame._data = None
    yield
    wordgame.Wordgame._data = None


def test_wordgame_load_data(uncache_wordgame_data):
    assert wordgame.Wordgame._data is None
    wordgame.Wordgame.load_word_data()
    assert wordgame.Wordgame._data is not None

    # show loading with cache
    id1 = id(wordgame.Wordgame._data)
    wordgame.Wordgame.load_word_data()
    id2 = id(wordgame.Wordgame._data)
    assert id1 == id2


def test_wordgame_categories():
    wordgame.Wordgame.load_word_data()
    assert "test" in wordgame.Wordgame._data.keys()
    categories = wordgame.Wordgame.word_categories()
    assert isinstance(categories, list)
    assert isinstance(categories[0], str)
    assert "test" not in categories
