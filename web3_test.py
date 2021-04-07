import json
from web3 import Web3

ganache_url = 'http://127.0.0.1:8545'
web3 = Web3(Web3.HTTPProvider(ganache_url))

print(web3.eth.blockNumber)

account1 = '0xBbdC92622223aB770d5EfD91a4Bc596008e0d47b'
account2 = '0xb5373e0Ab10F5A6FC53574474eDeEe17371F8518'

private_key = '0x07af7fe1c1c030860f84c4556d0286cd84f9cda1f086145e87e2b2f4ad61755f'

# get the nonce
nonce = web3.eth.getTransactionCount(account1)
# build a transaction
tx = {
    'nonce': nonce,
    'to': account2,
    'value': web3.toWei(1, 'ether'),
    'gas': 2000000,
    'gasPrice': web3.toWei('50', 'gwei')
}

# sign the transaction
signed_tx = web3.eth.account.signTransaction(tx, private_key)
# send the transaction
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
print(tx_hash)
# get transaction hash
