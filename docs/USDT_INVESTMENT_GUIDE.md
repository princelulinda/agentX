# Guide d'Investissement USDT

Ce guide détaille les étapes et les API nécessaires pour effectuer des investissements en USDT sur notre plateforme.

## Table des matières
1. [Création du Wallet USDT](#1-création-du-wallet-usdt)
2. [Dépôt de USDT](#2-dépôt-de-usdt)
3. [Vérification du Solde](#3-vérification-du-solde)
4. [Création d'un Investissement](#4-création-dun-investissement)
5. [Suivi des Investissements](#5-suivi-des-investissements)

## 1. Création du Wallet USDT

### Créer un nouveau wallet USDT
```http
POST /api/investments/wallet/
Content-Type: application/json
Authorization: Bearer <votre_token>

{
    "address": "0xVotreAdresseEthereum"
}
```

#### Réponse Réussie (200 OK)
```json
{
    "id": 1,
    "address": "0xVotreAdresseEthereum",
    "balance": "0.000000",
    "created_at": "2025-01-21T08:25:09Z",
    "updated_at": "2025-01-21T08:25:09Z"
}
```

#### Erreurs Possibles
- 400 Bad Request : "Vous avez déjà un portefeuille USDT"
- 401 Unauthorized : "Authentication credentials were not provided"

## 2. Dépôt de USDT

### Étape 1 : Envoi des USDT
Envoyez vos USDT à l'adresse de l'entreprise :
```
0x19563cF5bB4935043a9220eBc292456A72380B1D
```

### Étape 2 : Enregistrement du dépôt
```http
POST /api/investments/transactions/deposit/
Content-Type: application/json
Authorization: Bearer <votre_token>

{
    "tx_hash": "0x123...votre_hash_de_transaction"
}
```

#### Réponse Réussie (200 OK)
```json
{
    "id": 1,
    "transaction_type": "DEPOSIT",
    "amount": "1000.000000",
    "status": "COMPLETED",
    "tx_hash": "0x123...",
    "created_at": "2025-01-21T08:30:00Z"
}
```

#### Erreurs Possibles
- 400 Bad Request : 
  - "Transaction hash is required"
  - "Invalid transaction"
  - "Invalid destination address"

## 3. Vérification du Solde

### Vérifier le solde du wallet
```http
GET /api/investments/   
Authorization: Bearer <votre_token>
```

#### Réponse Réussie (200 OK)
```json
{
    "blockchain_balance": "1000.000000",
    "local_balance": "1000.000000"
}
```

## 4. Création d'un Investissement

### Voir les plans disponibles
```http
GET /api/investments/plans/
Authorization: Bearer <votre_token>
```

### Créer un investissement
```http
POST /api/investments/my-investments/
Content-Type: application/json
Authorization: Bearer <votre_token>

{
    "plan": 1,
    "amount_invested": "1000.00",
    "currency": "USDT"
}
```

#### Réponse Réussie (201 Created)
```json
{
    "id": 1,
    "plan_name": "Plan Croissance",
    "amount_invested": "1000.00",
    "currency": "USDT",
    "status": "ACTIVE",
    "current_value": "1000.00",
    "usdt_transaction_details": {
        "id": 2,
        "transaction_type": "INVESTMENT",
        "amount": "1000.000000",
        "status": "COMPLETED"
    }
}
```

#### Erreurs Possibles
- 400 Bad Request :
  - "Solde USDT insuffisant"
  - "Vous devez créer un portefeuille USDT avant d'investir en USDT"
  - "Le montant minimum d'investissement pour ce plan est de X"

## 5. Suivi des Investissements

### Liste de vos investissements
```http
GET /api/investments/my-investments/
Authorization: Bearer <votre_token>
```

### Calculer les gains d'un investissement
```http
POST /api/investments/my-investments/{investment_id}/calculate_earnings/
Authorization: Bearer <votre_token>
```

#### Réponse Réussie (200 OK)
```json
{
    "earnings": "50.00",
    "current_value": "1050.00",
    "last_update": "2025-01-21T08:45:00Z"
}
```

## Historique des Transactions

### Voir toutes vos transactions USDT
```http
GET /api/investments/transactions/
Authorization: Bearer <votre_token>
```

#### Réponse Réussie (200 OK)
```json
[
    {
        "id": 1,
        "transaction_type": "DEPOSIT",
        "amount": "1000.000000",
        "status": "COMPLETED",
        "tx_hash": "0x123...",
        "created_at": "2025-01-21T08:30:00Z"
    },
    {
        "id": 2,
        "transaction_type": "INVESTMENT",
        "amount": "1000.000000",
        "status": "COMPLETED",
        "created_at": "2025-01-21T08:35:00Z"
    }
]
```

## Notes Importantes

1. **Sécurité**
   - Gardez votre clé privée en sécurité
   - Ne partagez jamais vos identifiants
   - Vérifiez toujours l'adresse de destination des USDT

2. **Délais de Transaction**
   - Les dépôts USDT nécessitent des confirmations blockchain
   - Le temps de confirmation peut varier selon le réseau

3. **Limites**
   - Respectez les montants minimums d'investissement
   - Assurez-vous d'avoir suffisamment de USDT avant d'investir

4. **Support**
   - En cas de problème avec une transaction, contactez le support avec le hash de transaction
   - Gardez une trace de tous vos hash de transaction
