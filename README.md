# DNB Annales Scraper 📚

Un outil Python simple et efficace pour scraper et télécharger les annales du Diplôme National du Brevet (DNB) depuis le site officiel du ministère de l'Éducation nationale français.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Fonctionnalités

- ✅ **Scraping avec Selenium** - Navigation automatique dans les pages avec JavaScript
- ✅ **Pagination automatique** - Parcourt toutes les pages
- ✅ **Extraction de liens** `/document/*/download` avec métadonnées
- ✅ **Téléchargement concurrent** avec gestion de threads
- ✅ **Organisation automatique** par année et matière
- ✅ **Extraction automatique des ZIP** - Décompression immédiate après téléchargement
- ✅ **Support multi-format** - PDF, ZIP, DOC, DOCX, ODT, etc.
- ✅ **Gestion d'erreurs robuste** avec retry automatique
- ✅ **Rate limiting** pour respecter le serveur
- ✅ **Logging complet** avec rotation de fichiers et log d'erreurs séparé
- ✅ **Interface CLI** intuitive
- ✅ **Mode headless** ou visible pour le debugging

## 📋 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- **Google Chrome** (navigateur)
- Connexion Internet

### Installation de ChromeDriver

ChromeDriver est géré automatiquement par Selenium 4.15+. Assurez-vous simplement que Google Chrome est installé.

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/taieb1919/sokratika-ExamScrapper.git
cd sokratika-ExamScrapper
```

### 2. Créer un environnement virtuel (recommandé)

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## 📖 Utilisation

### Interface en ligne de commande (CLI)

Le projet fournit une interface CLI unifiée avec des options flexibles :

#### Utilisation de base

```bash
# Scraper et afficher le résumé (par défaut)
python main.py

# Limiter le nombre de pages parcourues (ex: 2 premières pages)
python main.py --pages 2
```

#### Validation des données

```bash
# Valider les entrées et générer validation_report.csv
python main.py --validate

# Valider en limitant à 2 pages
python main.py --validate --pages 2
```

#### Téléchargement des PDFs

```bash
# Télécharger tous les PDFs après scraping
python main.py --download

# Télécharger en limitant à 2 pages
python main.py --download --pages 2

# Valider d'abord, puis télécharger seulement si validation OK
python main.py --validate --download
```

#### Options avancées

```bash
# Changer le niveau de logging
python main.py --log-level DEBUG --download

# Spécifier un fichier de log personnalisé
python main.py --log-file custom.log --download
```

### Utilisation programmatique

```python
from src.scraper import DNBScraper
from src.downloader import FileDownloader

# Scraping
scraper = DNBScraper()
scraper.extract_pdf_links()
entries = scraper.structured_entries

# Téléchargement
downloader = FileDownloader()
urls = [f.download_url for entry in entries for f in entry.files]
results = downloader.batch_download(urls=urls)

print(f"Téléchargés: {len(results['successful'])}")
print(f"Échecs: {len(results['failed'])}")
```

## 🗂️ Structure du projet

```
sokratika-ExamScrapper/
│
├── src/                        # Code source principal
│   ├── __init__.py            # Initialisation du package
│   ├── scraper.py             # Module de scraping (DNBScraper)
│   ├── downloader.py          # Module de téléchargement (PDFDownloader)
│   ├── parser.py              # Analyseur de métadonnées (MetadataParser)
│   └── utils.py               # Fonctions utilitaires
│
├── config/                    # Configuration
│   └── settings.py            # Paramètres de configuration
│
├── data/                      # Données téléchargées
│   ├── raw/                   # Fichiers téléchargés (organisés par année/matière)
│   │   ├── 2024/              # Organisation par année
│   │   │   ├── Français/      # Organisation par matière
│   │   │   │   ├── fichier.pdf
│   │   │   │   ├── archive.zip
│   │   │   │   └── archive/   # Dossier extrait automatiquement
│   │   │   └── Mathématiques/
│   │   └── 2023/
│   └── metadata/              # Fichiers JSON avec métadonnées
│
├── logs/                      # Fichiers de logs
│   ├── dnb_scraper_YYYY-MM-DD.log  # Log complet avec rotation
│   └── errors_only.log             # Log des erreurs uniquement
│
│
├── main.py                    # Point d'entrée CLI
├── requirements.txt           # Dépendances Python
├── setup.py                   # Configuration du package
└── README.md                  # Ce fichier
```

## 📊 Métadonnées extraites

Le scraper extrait automatiquement :

- **Année** : Depuis le nom de fichier (ex: "24" → "2024")
- **Matière** : Français, Mathématiques, Histoire-Géographie, etc.
- **Session** : normale, remplacement
- **Série** : générale, professionnelle
- **Type de document** : sujet ou correction

## ⚙️ Configuration

### Variables d'environnement (optionnel)

Créez un fichier `.env` pour personnaliser :

```env
# Principales options
SELENIUM_HEADLESS=True         # Mode headless
MAX_WORKERS=5                  # Téléchargements concurrents
LOG_LEVEL=INFO                 # Niveau de log
```

## 📁 Organisation des fichiers

Les fichiers téléchargés sont automatiquement organisés :

```
data/raw/
├── 2024/
│   ├── Français/
│   │   ├── 24genfrdag1_v11.pdf
│   │   ├── 24genfrdag1_corrige.pdf
│   │   ├── archive_documents.zip
│   │   └── archive_documents/     # Dossier extrait automatiquement
│   │       ├── document1.pdf
│   │       └── document2.pdf
│   ├── Mathématiques/
│   │   ├── 24genmathag1_v11.pdf
│   │   └── 24genmathag1_corrige.pdf
│   └── Histoire-Géographie/
│       └── 24genhisgeoag1_v11.pdf
└── 2023/
    └── ...
```

**Note** : Les fichiers ZIP sont automatiquement extraits dans un dossier du même nom (sans l'extension `.zip`). Le fichier ZIP original est conservé.

## 🛡️ Bonnes pratiques

- **Respect du serveur** : Rate limiting, retry automatique
- **Logging complet** : Logs avec rotation + log d'erreurs séparé (`errors_only.log`)
- **Code qualité** : Type hints, docstrings, gestion d'erreurs

## 🔧 API

```python
# Scraper
scraper = DNBScraper()
scraper.extract_pdf_links()
entries = scraper.structured_entries

# Téléchargeur
downloader = FileDownloader()
downloader.batch_download(urls)
```

## 🐛 Dépannage

### ChromeDriver not found

```bash
# Selenium 4.15+ gère ChromeDriver automatiquement
# Vérifiez que Chrome est installé
```

### Erreur de connexion

```bash
# Vérifier la connectivité
python -c "import requests; print(requests.get('https://eduscol.education.fr').status_code)"
```

### ImportError

```bash
# Réinstaller les dépendances
pip install --force-reinstall -r requirements.txt
```

## 📝 Exemples

### Obtenir des statistiques

```python
from src.scraper import DNBScraper

scraper = DNBScraper()
scraper.extract_pdf_links()
stats = scraper.get_summary_dict()

print(f"Total: {stats['total']}")
print(f"Années: {stats['years']}")
print(f"Matières: {stats['subjects']}")
```

### Télécharger uniquement 2024

```python
from src.scraper import DNBScraper
from src.downloader import FileDownloader

scraper = DNBScraper()
scraper.extract_pdf_links()

# Filtrer 2024
entries_2024 = [e for e in scraper.structured_entries
                if e.session.value.startswith('2024')]

urls_2024 = [f.download_url for entry in entries_2024 for f in entry.files]

downloader = FileDownloader()
results = downloader.batch_download(urls=urls_2024)
```

## ⚖️ Licence

MIT License - Voir le fichier `LICENSE` pour plus de détails.

## ⚠️ Disclaimer

Ce projet est destiné à un usage éducatif et respecte les conditions d'utilisation du site eduscol.education.fr.
