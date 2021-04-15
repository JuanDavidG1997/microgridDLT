from web3 import Web3
import json

infura_url = 'https://mainnet.infura.io/v3/9187eaca63a448179ac1dc61a76e4665'
web3 = Web3(Web3.HTTPProvider(infura_url))

latest = web3.eth.blockNumber
print(latest)
print(web3.eth.getBlock(latest))

for i in range(0,10):
    print(web3.eth.getBlock(latest-i))
