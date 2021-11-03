# Blockchain - Agent class definition

class Block:

    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        """ Initialize agent instance.

        Args:
            index (int): corresponding index of the block
            transactions (list): list of transactions of the corresponding block
            timestamp (): timestamp of the block
            previous_hash (): hash of the previous block
            nonce (): arbitraty number
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # difficulty of our PoW algorithm
    difficulty = 2

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            return False

        if not Blockchain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        self.unconfirmed_transactions = []

        return True


class Wrapper:
    def __init__(self):
        self.blockchain = Blockchain()
        self.blockchain.create_genesis_block()
        self.peers = []

    def new_transaction(self, tx_data):
        required_fields = ['author', 'content']

        for field in required_fields:
            if not tx_data.get(field):
                return "Invalid transaction data"
        tx_data['timestamp'] = time.time()
        self.blockchain.add_new_transaction(tx_data)

        return 'Success'

    def get_chain(self):
        chain_data = []
        for block in self.blockchain.chain:
            chain_data.append(block.__dict__)
            return json.dumps({"length": len(chain_data), "chain": chain_data, "peers": list(self.peers)})

    def mine_unconfirmed_transactions(self):
        result = self.blockchain.mine()
        if not result:
            return "No transactions to mine"
        else:
            # Making sure we have the longest chain before announcing to the network
            chain_length = len(self.blockchain.chain)

            peers = []
            for peer in self.peers:
                new_peer = {'address': peer['address'], 'chain': self.blockchain.chain}
                peers.append(new_peer)
            self.peers = peers

            self.consensus()

            return "Block #{} is mined.".format(self.blockchain.last_block.index)

    def register_new_peers(self, node_address):
        if not node_address:
            return "Invalid data"

        peer = {'address': node_address, 'chain': None}
        self.peers.append(peer)
        return self.get_chain()

    def create_chain_from_dump(self, chain_dump):
        generated_blockchain = Blockchain()
        generated_blockchain.create_genesis_block()
        for idx, block_data in enumerate(chain_dump):
            if idx == 0:
                continue  # skip genesis block
            block = Block(block_data["index"],
                          block_data["transactions"],
                          block_data["timestamp"],
                          block_data["previous_hash"],
                          block_data["nonce"])
            proof = block_data['hash']
            added = generated_blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
        return generated_blockchain

    def verify_and_add_block(self, block_data):
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])

        proof = block_data['hash']
        added = self.blockchain.add_block(block, proof)

        if not added:
            return "The block was discarded by the node", 400

        return "Block added to the chain", 201


    def create_chain_from_dump(self, chain_dump):
        generated_blockchain = Blockchain()
        generated_blockchain.create_genesis_block()
        for idx, block_data in enumerate(chain_dump):
            if idx == 0:
                continue  # skip genesis block
            block = Block(block_data["index"],
                          block_data["transactions"],
                          block_data["timestamp"],
                          block_data["previous_hash"],
                          block_data["nonce"])
            proof = block_data['hash']
            added = generated_blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
        return generated_blockchain

    def get_pending_tx(self):
        return json.dumps(self.blockchain.unconfirmed_transactions)


    def consensus(self):
        """
        Our naive consnsus algorithm. If a longer valid chain is
        found, our chain is replaced with it.
        """
        longest_chain = None
        current_len = len(self.blockchain.chain)

        for node in self.peers:
            length = len(node['chain'])
            chain = node['chain']
            if length > current_len and self.blockchain.check_chain_validity(chain):
                current_len = length
                longest_chain = chain

        if longest_chain:
            blockchain = longest_chain
            return True

        return False

class Agent:
    def __init__(self, demand, supply, node, address, price, wrapper):
        self.demand = demand
        self.supply = supply
        self.node = node
        self.address = address
        self.price = price
        self.register_peer(wrapper)

    def register_peer(self, wrapper):
        wrapper.register_new_peers(self.address)

    def publish_energy_info(self, step):
        agents_info = {}
        agents_info['node'] = self.node
        agents_info['demand'] = self.demand[step]
        agents_info['supply'] = self.supply[step]
        agents_info['consumption'] = self.demand[step] - self.supply[step]
        agents_info['price'] = self.price[step]

        return self.node, agents_info

    def get_demand(self):
        return self.demand

    def get_supply(self):
        return self.supply

    def get_node(self):
        return self.node

    def get_address(self):
        return self.address

    def get_consumption(self):
        return self.consumption

    def get_prices(self):
        return self.price

    def set_payment_data(self, data):
        self.payment_data = data

    def pay_power(self, step, wrapper):
        """ Send power payment

        Args:
            step (float): step running at the moment.
        """
        unpack_data = self.payment_data
        for index, node in enumerate(unpack_data['node']):
            tx_data = {'author': self.address,
                       'content': {'payment': unpack_data['price']*unpack_data['power'][index],
                                   'seller': unpack_data['seller']}}
            wrapper.new_transaction(tx_data)
