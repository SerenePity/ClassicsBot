import os
import scholasticus

token = os.environ['token']
client = scholasticus.Scholasticus("/")
client.run(token)
