# License Key Management Tool

Outil CLI pour gérer les clés de licence Notes2Notion durant la phase de beta testing.

## Installation

```bash
cd admin_tools
pip install -r requirements.txt
```

## Utilisation

### Générer des clés de licence

Générer une seule clé :
```bash
python license_manager.py generate
```

Générer plusieurs clés :
```bash
python license_manager.py generate --count 10 --notes "Batch beta testing #1"
```

Sauvegarder dans un fichier :
```bash
python license_manager.py generate --count 50 --notes "Batch #2" --output keys_batch2.txt
```

### Lister les clés

Toutes les clés :
```bash
python license_manager.py list
```

Seulement les clés actives :
```bash
python license_manager.py list --active-only
```

### Vérifier une clé

```bash
python license_manager.py check BETA-ABCD-1234-EFGH
```

### Révoquer une clé

```bash
python license_manager.py revoke BETA-ABCD-1234-EFGH
```

### Afficher les statistiques

```bash
python license_manager.py stats
```

## Format des clés

Les clés sont au format : `BETA-XXXX-XXXX-XXXX`

- Caractères exclus pour éviter la confusion : 0, O, I, 1
- Génération cryptographiquement sécurisée avec `secrets`
- Insensible à la casse (automatiquement converti en majuscules)

## Notes

- Les clés sont uniques et à usage unique (une seule personne par clé)
- Pas de date d'expiration
- Une fois révoquée, une clé ne peut plus être utilisée
- Les clés sont stockées dans la base de données MySQL de Notes2Notion

## Configuration

Le script utilise automatiquement le fichier `.env` à la racine du projet pour se connecter à la base de données.

Variables nécessaires :
- `DATABASE_URL` : URL de connexion à MySQL

Exemple :
```
DATABASE_URL=mysql+pymysql://notes2notion:notes2notion@mysql:3306/notes2notion?charset=utf8mb4
```
