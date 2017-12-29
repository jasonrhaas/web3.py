from eth_keys.datatypes import PrivateKey
from eth_utils import is_same_address

from web3.utils.datastructures import HexBytes
from web3.exceptions import InvalidAddress
# from web3.utils.signing import LocalAccount

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def construct_transaction_signing_middleware(private_key):
    """Intercept a transaction in flight and sign it.

    Args:
        private_key (TYPE): Private key used to sign the transaction.
                            Accepts the following formats:
                            - `PrivateKey` object from `eth-keys`
                            - `LocalAccount` object from `web3.eth.account`
                            - raw bytes
                            - TODO: hex encoded string


    Returns:
        TYPE: Description
    """

    valid_key_types = (PrivateKey, HexBytes, bytes)

    _private_key = private_key if isinstance(private_key, valid_key_types) else None
    if not _private_key:
        raise ValueError('Private Key is invalid.')

    def transaction_signing_middleware(make_request, web3):
        def middleware(method, params):
            # Only operate on the `eth.sendTransaction` method
            # Only operate on if the private key matches the public key in the transaction
            # Note: params == transaction in this case.
            if method != 'eth_sendTransaction':
                return make_request(method, params)

            transaction = params
            transaction_from_address = transaction.get('from')
            private_key_address = web3.eth.account.privateKeyToAccount(_private_key).address

            if not is_same_address(transaction_from_address, private_key_address):
                return make_request(method, params)

            if 'gas' not in transaction:
                try:
                    transaction['gas'] = web3.eth.estimateGas(transaction)
                except ValueError:
                    # Raise Error?
                    transaction['gas'] = 21000
            if 'gas_price' not in transaction:
                transaction['gasPrice'] = web3.eth.gasPrice
            if 'chainId' not in transaction:
                transaction['chainId'] = 1
            if 'nonce' not in transaction:
                try:
                    transaction['nonce'] = web3.eth.getTransactionCount(transaction_from_address)
                except InvalidAddress:
                    # Raise error?
                    transaction['nonce'] = 1

            signed = web3.eth.account.signTransaction(transaction, _private_key)
            raw_transaction = signed.rawTransaction

            return make_request(method='eth_sendRawTransaction', params=[raw_transaction])
        return middleware
    return transaction_signing_middleware
