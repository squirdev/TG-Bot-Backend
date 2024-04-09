# SWAPS AND BURN WSS SERVER

## General use

The WSS should be running (see domain conf and other related ops tasks), 
during this time, the server will start watching burns and swaps 
(based off mongo data)

To register to the WSS and start watching, you will need to provide:
- the url of the server (ie localhost: ws://localhost:4000)
- an API key (defined in mongoDB for easier rolling)
- the event you want to subscribe (swap, burn...)

The server handle 4 events:
- **swaps** => register to swaps
- **add_token** => adds a token
- **remove_token** => removes a token

All of those details can be seen in **CLIENT** section of **utils/websocket_utils.py** (ie: subscribe()) 

When the client is subscribed, then it will receive all the associated data,
sent by this server while fetching onchain events.

## Features
- swap watch
- telegram utils
- api key (mongo)
- wss subscription
- add/remove tokens (mongo/ram)
- providers / chain conf (constants.py & web3_utils)
- rolling RPC urls (each calls)

### Telegram utils
I isolated telegram posting logic into an associated class, so far I had only
one bot, so I could use it as an example but there might be other logics to implements
for the others

### API key
In order to avoid unexpected use of your API, you must authenticate with a simple
API key system, fetching data from mongo for easy roll.

### Swap watch
The swap watch will be fed by the data to track from both mongo and RAM held
into swap_tracking_utils.
Additions, will add to both storages, but mongo load will likely only be used
for fresh start/reboots...
See here if need to handle different groups (channels) so far system is build here
but those data aren't returned from the WSS broadcasts

### Add/remove token
To add or to remove a token, all the associated data must be sent to the WSS server
after sending the associated event.
Adding or removing a token will update the database as well.

Examples can be found on add_token and remove_token functions from websocket_utils.py

## Setting up
Most of the conf so far is stored into **constants.py** due to the low impact of an exploit,
but it can be migrated to env if needed.

Only exception (apart from internal constants) are the chains/provider conf which is held into **utils/web3_utils.py**'s
PROVIDERS constants which holds all necessary data for the scripts. Here you can add several others if needed,
following the same logic:
- chain id indexing
- most params are obvious, some maybe a bit less:
  - startBlock: the default start block to register events (note there's a limit of 20k blocks, enforced around 10k)
  - blockIntervalSeconds: the average time for a block to be created on this chain = refresh rate (current values are based of chain data, lowering them would incur more call for the same results)

Other conf or related data are stored into mongodb/ram

### Conf
#### Constants
Here you must provide:
- MONGO_CONNECT_URL: your mongo connection string
- [\*]_RPC: the lists of RPC URLs you wish to use for each provider (so far ETH / BSC)

Other elements have predefined value and can be customized if needed

#### Web3 utils
Everything is already set up here, but other providers can be added if needed

#### MongoDb
Apart from initial mock token data, here important notice is api key "secret" value that can be changed whenever it is needed
Note: you will also need to update this value sent from WSS clients in such a situation

### Run
Whenever it is set up, you can run **main.py**
This script will start a thread per chain for swap event tracking and a thread per burn event tracking,
it will also start the WSS server, ready for incoming connections (that will be displayed among with disconnect into debug console)

When at least a client will be connected to listen an even, the server will start recording and broadcasting
to clients the associated events

### Connect
As per code in **config/websocket_utils.py** and **demo_[\*].py** that can be used as example,
both show the global logic of each interaction

#### Common
Both will need to start off connecting to websocket
```python
websockets.connect(uri) as websocket:
```

Then in order to authenticate, will need to send the api_key
```python
await websocket.send(api_key)
```

If at that point you successfully connected with the key secret, you will need to send the event you want to register/trigger
```python
await websocket.send(event)
```

#### Subscribe to events
When you subscribe to an event following previous instructions, each time you will await for websocket.recv,
the client will be waiting for an event from the WSS server (which will be delivered if existing / amount > 0 / len(transactions) > 0)
```python
while True:
    response = await websocket.recv()
    print(json.loads(response))
```

#### Token add/remove
For add_token and remove_token parameters needs to be passed as json, you will get back a response on the addition
Note: failure on an addition can mean the token was already in the list
Here is a simple example from **demo_main_client_add_token.py** logic is similar for removal
```python
await websocket.send(api_key)
await websocket.send('add_token')

new_token_data = {
  'chain': chain,
  'name': name,
  'decimals': decimals,
  'address': address,
  'pair': pair,
  'isToken0': is_token_0,
  'group': group
}

await websocket.send(json.dumps(new_token_data))
        
response = await websocket.recv()
json_response = json.loads(response)
```

## Going further 

### RPC rates limit
If needed, to fight rates limits, several RPC url can be used and will roll during the run
It is also possible in the future to scale by switching from http providers to wss providers
where querying onchain events (for chains supporting it and easy access to free tier).

### Scaling
So far the single instance should be able to handle some load, if needed for future expansion,
logics could be split into separate WSS servers (per chain / per events as well) and distinguishing database fields per instance or so

### Refactoring
I made sure the service is efficient, easily reusable, upgradable... But considering the time constraints, I still wanted 
to deliver what I planned so far (WSS instead of an HTTP API) which is efficient and can be used by several of your bots or services independently.
Most relevant constraints are RPC calls (ratio keys/tracked events) and instance specs (which shouldn't require that much either except for huge connection pools).
As a consequence some code at that point could benefit from refactoring (but here could depend on your global/other usecases),
but the development has been made such that it can evolve and scale in a near future.
