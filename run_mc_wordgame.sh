#!/bin/bash

python twitch_chatbot.py --verbose \
    --wordgame "I'm thinking of the name of an item that you can collect in Minecraft." \
    --wordlist minecraft_1.20_item_list.yml \
    --moderator fretboardfreak \
    ${@}
