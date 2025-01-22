from web3 import Web3
from decimal import Decimal
from django.conf import settings
import json

class BlockchainClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.INFURA_URL))
        self.company_wallet = settings.COMPANY_WALLET_ADDRESS
        self.company_private_key = settings.COMPANY_WALLET_PRIVATE_KEY
        
        # Charger l'ABI du contrat USDT
        with open(settings.USDT_ABI_PATH) as f:
            self.contract_abi = json.load(f)
        
        # Initialiser le contrat USDT
        self.usdt_contract = self.w3.eth.contract(
            address=settings.USDT_CONTRACT_ADDRESS,
            abi=self.contract_abi
        )

    def send_usdt(self, to_address: str, amount: Decimal) -> str:
        """
        Envoie des USDT du wallet de la compagnie vers l'adresse spécifiée
        
        Args:
            to_address: Adresse du portefeuille destinataire
            amount: Montant en USDT à envoyer
            
        Returns:
            str: Hash de la transaction
        """
        try:
            # Convertir le montant en unités USDT (6 décimales)
            amount_wei = int(amount * Decimal('1000000'))
            
            # Construire la transaction
            nonce = self.w3.eth.get_transaction_count(self.company_wallet)
            
            # Préparer la transaction de transfert USDT
            transfer_txn = self.usdt_contract.functions.transfer(
                to_address,
                amount_wei
            ).build_transaction({
                'chainId': settings.CHAIN_ID,
                'gas': 100000,  # Limite de gas
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Signer la transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transfer_txn,
                self.company_private_key
            )
            
            # Envoyer la transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Attendre la confirmation de la transaction
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if tx_receipt['status'] == 1:  # Transaction réussie
                return self.w3.to_hex(tx_hash)
            else:
                raise Exception("La transaction a échoué")
                
        except Exception as e:
            raise Exception(f"Erreur lors de l'envoi des USDT: {str(e)}")

    def verify_transaction(self, tx_hash: str) -> dict:
        """
        Vérifie une transaction USDT et retourne ses détails
        
        Args:
            tx_hash: Hash de la transaction à vérifier
            
        Returns:
            dict: Détails de la transaction avec les clés :
                - valid (bool): True si la transaction est valide
                - amount (Decimal): Montant de la transaction
                - to_address (str): Adresse du destinataire
                - error (str): Message d'erreur si la transaction n'est pas valide
        """
            # Récupérer les détails de la transaction
        tx = self.w3.eth.get_transaction(tx_hash)
        tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        try:
            
            if not tx_receipt['status']:
                return {
                    'valid': False,
                    'error': 'La transaction a échoué'
                }

            # Décoder les données de la transaction
            decoded_input = self.usdt_contract.decode_function_input(tx['input'])
            print(decoded_input)
            # Vérifier que c'est bien un transfert USDT
            if decoded_input[0].fn_name != 'transfer':
                return {
                    'valid': False,
                    'error': 'Ce n\'est pas une transaction de transfert USDT'
                }
            
            # Extraire le montant et l'adresse de destination
            amount = Decimal(decoded_input[1]['_value']) / Decimal('1000000')  
            to_address = decoded_input[1]['_to']

            return {
                'valid': True,
                'amount': amount,
                'to_address': to_address,
                'error': None
            }

        except Exception as e:
            print(e)
            return {
                'valid': False,
                'error': str(e)
            }
