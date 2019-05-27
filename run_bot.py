import sys
import scholasticus

token = sys.argv[1]
client = scholasticus.Scholasticus(">")
client.run(token)