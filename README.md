# bar-counter-discordbot
This bot allows you to drink your mates in discord-chat :D  
Built using Python, discord.py and peewee.  

## Concept
When bot serves an drink, it tells a random joke.  
Per day number of portions is limited. Every day happens resupply of drinks.

Each drink has an 'intoxication' parameter. Intoxication is in bounds from 0% to 100%.  
When person accumulate 100% intoxication, bot kicks him from voice chat.  
Each minute intoxication lowers by 1%.

## Commands
* `?drink <drink_name>`  
Consume a drink.
* `?serve <drink_name> <to1> ... <toN>`  
Serve a drink to people. `<toI>` can be username or mention.  
Prompts people to drink. Mentioned members can accept or decline it.
* `?add <drink_name> [intoxication=20] [portion_size=100] [portions_per_day=10]`  
Add drink to the bar. Portion size in milliliters, intoxication from 0 to 100. Portions per day and portion
size are lower than 10000.
Requires role "barman".
* `?remove <drink_name>`  
Remove drink from the bar. Requires role "barman".
* `?list`  
Return the list of drinks.
* `?restock`  
Manually restock drinks. Requires role "barman".
* `?reset`  
Remove all drinks from the bar. Requires role "barman".
* `?reset 1`  
Remove all drinks from the bar and add default drinks. Requires role "barman".

## Localization
Currently supported languages: russian (ru_RU)

## Installation
1) Register a new bot on https://discordapp.com/developers/applications/ and get token on "build-a-bot" page.
2) Install python3 on your server.
3) Execute commands:  
   If you're using Ubuntu:
   ```shell script
   git clone https://github.com/6rayWa1cher/bar-counter-discordbot
   cd bar-counter-discordbot
   pip3 install virtualenv
   python3 -m virtualenv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   mkdir logs
   echo -e "default:\n  TOKEN:<YOUR_TOKEN>\n  LOGS_LOCATION: ${PWD}/logs/\n  DB_LOCATION: ${PWD}/sqlite.db\n" >> config/settings.local.yaml
   echo -e "export ROOT_PATH_FOR_DYNACONF='${PWD}/config'" >> .env
   ```
4) Fill `config/settings.local.yaml` with your own discord bot token.
5) Execute command:
   ```shell script
   python3 -m barcounter
   ```
6) To start bot after stop:
   ```shell script
   cd bar-counter-discordbot
   source venv/bin/activate
   python3 -m barcounter
   ```
7) To add a bot to your server, modify and click the url:
`https://discordapp.com/oauth2/authorize?client_id=<YOUR_BOT_CLIENT_ID>&scope=bot&permissions=285215808`

## Contributing
You're always welcome with ideas, issues, localizations and other help! 