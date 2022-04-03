import os

import classics_bot

token = os.environ['token']
client = classics_bot.ClassicsBot("")
client.run(token)
