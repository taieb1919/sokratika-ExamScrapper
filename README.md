# DNB Annales Scraper 📚

Un outil Python simple et efficace pour scraper et télécharger les annales du Diplôme National du Brevet (DNB) depuis le site officiel du ministère de l'Éducation nationale français.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Fonctionnalités

- ✅ **Scraping automatique** - Navigation et pagination avec Selenium
- ✅ **Téléchargement concurrent** - Multi-threading avec gestion d'erreurs
- ✅ **Téléchargement pendant pagination** - Mode optimisé pour gros volumes
- ✅ **Organisation intelligente** - Par année, matière et extraction ZIP automatique
- ✅ **Support multi-format** - PDF, ZIP, DOC, DOCX, ODT, etc.
- ✅ **Interface CLI** - Commandes simples et validation des données

## 📊 Structure des données extraites

### Format des entrées (`ExamEntry`)

Chaque ligne du tableau HTML devient une `ExamEntry` avec :

- **ID** : Numéro séquentiel (1, 2, 3...)
- **Session** : NORMAL, REMPLACEMENT, etc.
- **Discipline** : FR_DICTEE, FR_GRAM_COMP, etc.
- **Série** : GENERALE, PROFESSIONNELLE
- **Localisation** : METROPOLE, AM_NORTH, AM_SOUTH, etc.
- **Files** : Liste des fichiers de cette entrée

### Construction des noms de fichiers

Format : `{ID}_{SESSION}_{DISCIPLINE}_{SERIE}_{LOCALISATION}_{FILE_ID}`

**Exemple** : `1_NORMAL_FR_DICTEE_GENERALE_AM_NORTH_63474`

### Métadonnées extraites par fichier

- **filename** : Nom original (ex: "24genfrdag1_v11.pdf")
- **file_id** : ID numérique du document (ex: "63414")
- **download_url** : URL complète de téléchargement
- **filename_for_save** : Nom structuré pour sauvegarde
- **Année** : Depuis le nom de fichier (ex: "24" → "2024")
- **Matière** : Français, Mathématiques, Histoire-Géographie, etc.
- **Session** : normale, remplacement
- **Série** : générale, professionnelle
- **Type de document** : sujet ou correction
- **Localisation** : Métropole, Antilles-Guyane, etc.

## 📋 Valeurs possibles des énumérations

### Sessions

- **NORMAL** : Session normale (juin)
- **REMPLACEMENT** : Session de remplacement (septembre)

### Disciplines

- **FR_DICTEE** : Français - Dictée
- **FR_GRAM_COMP** : Français - Grammaire/Compréhension
- **FR_REDACTION** : Français - Rédaction
- **HIST_GEO_EMC** : Histoire-Géographie-EMC
- **MATHS** : Mathématiques
- **SCIENCES** : Sciences (SVT, Physique, Chimie, Technologie)
- **LV_ALLEMAND** : Langue Vivante - Allemand
- **LV_ANGLAIS** : Langue Vivante - Anglais
- **LV_ARABE** : Langue Vivante - Arabe
- **LV_CHINOIS** : Langue Vivante - Chinois
- **LV_ESPAGNOL** : Langue Vivante - Espagnol
- **LV_GREC** : Langue Vivante - Grec
- **LV_HEBREU** : Langue Vivante - Hébreu
- **LV_ITALIEN** : Langue Vivante - Italien
- **LV_JAPONAIS** : Langue Vivante - Japonais
- **LV_PORTUGAIS** : Langue Vivante - Portugais
- **LV_RUSSE** : Langue Vivante - Russe
- **LV_TURC** : Langue Vivante - Turc

### Séries

- **GENERALE** : Série générale
- **PROFESSIONNELLE** : Série professionnelle
- **TOUTES** : Toutes séries

### Localisations

- **METROPOLE** : Métropole
- **AM_NORTH** : Amérique du Nord
- **AM_SOUTH** : Amérique du Sud
- **ANTIL_GUY** : Antilles, Guyane
- **ASIA** : Asie
- **LIBAN** : Liban
- **METRO_ANTIL_GUY** : Métropole et Antilles-Guyane
- **NOUVELLE_CAL** : Nouvelle-Calédonie
- **GROUPE_1** : Groupe 1
- **POLYNESIE** : Polynésie
- **PONDICHERY** : Pondichéry

## 📁 Organisation des fichiers

Les fichiers téléchargés sont automatiquement organisés **par matière uniquement** (pas par année) :

```
data/raw/
├── FR_DICTEE/                    # Français - Dictée
│   ├── 5_NORMAL_FR_DICTEE_GENERALE_METROPOLE_63118/
│   │   └── 24-GENFRDAME1 BA/     # Dossier extrait (2024)
│   ├── 122_NORMAL_FR_DICTEE_GENERALE_METROPOLE_54414/
│   │   └── 23-GENFRDAME1 BA/     # Dossier extrait (2023)
│   └── 8_NORMAL_FR_DICTEE_PROFESSIONNELLE_ANTIL_GUY_62947/
│       └── 24-PROFRDAAG1 BI/     # Dossier extrait (2024)
├── FR_GRAM_COMP/                 # Français - Grammaire/Compréhension
│   ├── 15_NORMAL_FR_GRAM_COMP_GENERALE_METROPOLE_63127/
│   │   └── 24-GENFRQGCME1 BA/    # Dossier extrait (2024)
│   ├── 131_NORMAL_FR_GRAM_COMP_GENERALE_ANTIL_GUY_54420/
│   │   └── 23-GENFRQGCAG1 BI/    # Dossier extrait (2023)
│   └── 19_NORMAL_FR_GRAM_COMP_PROFESSIONNELLE_METROPOLE_63166/
│       └── 24-PROFRQGCME1 BI/    # Dossier extrait (2024)
├── FR_REDACTION/                 # Français - Rédaction
│   ├── 25_NORMAL_FR_REDACTION_GENERALE_METROPOLE_63136/
│   │   └── 24-GENFRRME1 BA/      # Dossier extrait (2024)
│   └── 142_NORMAL_FR_REDACTION_GENERALE_ANTIL_GUY_54429/
│       └── 23-GENFRRAG1 BI/      # Dossier extrait (2023)
├── HIST_GEO_EMC/                 # Histoire-Géographie-EMC
│   ├── 35_NORMAL_HIST_GEO_EMC_GENERALE_METROPOLE_63141/
│   │   └── 24-GENHIGEME1 BA/     # Dossier extrait (2024)
│   └── 153_NORMAL_HIST_GEO_EMC_GENERALE_ANTIL_GUY_54438/
│       └── 23-GENHIGEAG1 BI/     # Dossier extrait (2023)
├── MATHS/                        # Mathématiques
│   ├── 67_NORMAL_MATHS_GENERALE_METROPOLE_63147/
│   │   └── 24-GENMATME1 BA/      # Dossier extrait (2024)
│   └── 189_NORMAL_MATHS_GENERALE_METROPOLE_54447/
│       └── 23-GENMATME1 BA/      # Dossier extrait (2023)
├── SCIENCES/                     # Sciences
│   ├── 45_NORMAL_SCIENCES_GENERALE_METROPOLE_63153/
│   │   └── 24-GENSCIME1 BA/      # Dossier extrait (2024)
│   └── 197_NORMAL_SCIENCES_GENERALE_METROPOLE_54453/
│       └── 23-GENSCIME1 BA/      # Dossier extrait (2023)
├── LV_ALLEMAND/                  # Langue Vivante - Allemand
│   └── 41_NORMAL_LV_ALLEMAND_TOUTES_METROPOLE_63162/
│       └── 24-GENLVAME1 BI/      # Dossier extrait (2024)
├── LV_ANGLAIS/                   # Langue Vivante - Anglais
│   └── 223_REMPLACEMENT_LV_ANGLAIS_TOUTES_ANTIL_GUY_54459/
│       └── 23-REMLVAG1 BI/       # Dossier extrait (2023)
└── [Autres matières...]          # LV_ESPAGNOL, LV_ITALIEN, etc.
```

**Notes importantes** :

- Les fichiers ZIP sont automatiquement extraits dans un dossier du même nom (sans l'extension `.zip`). Le fichier ZIP original est conservé.
- L'année est **encodée dans le nom du fichier** (ex: `24-GENFRDAME1` = 2024, `23-GENFRDAME1` = 2023) mais **pas dans la structure des dossiers**.
- Les fichiers de différentes années sont mélangés dans le même dossier de matière.

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
python main.py --validate -p 2
```

#### Téléchargement des PDFs

```bash
# Télécharger tous les PDFs après scraping (mode traditionnel)
python main.py --download

# Télécharger en limitant à 2 pages
python main.py --download -p 2

# Télécharger pendant la pagination (plus efficace pour gros volumes)
python main.py --download --download-during-scraping

# Télécharger pendant la pagination avec limite de pages
python main.py --download --download-during-scraping -p 3

# Valider d'abord, puis télécharger seulement si validation OK
python main.py --validate --download
```

#### Modes de téléchargement

Le scraper propose deux modes de téléchargement :

**Mode traditionnel** (par défaut) :

- Scraping complet de toutes les pages
- Affichage du résumé des statistiques
- Téléchargement en lot de tous les fichiers

**Mode optimisé** (`--download-during-scraping`) :

- Téléchargement immédiat après chaque page
- Plus efficace pour gros volumes de données
- Progression visible en temps réel
- Moins de consommation mémoire

```bash
# Mode traditionnel
python main.py --download

# Mode optimisé
python main.py --download --download-during-scraping
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
scraper.run_scraping()
entries = scraper.structured_entries

# Téléchargement
downloader = FileDownloader()
urls = [f.download_url for entry in entries for f in entry.files]
results = downloader.batch_download(urls=urls)

print(f"Téléchargés: {len(results['successful'])}")
print(f"Échecs: {len(results['failed'])}")
```

## 🔧 API

```python
# Scraper
scraper = DNBScraper()
scraper.run_scraping()
entries = scraper.structured_entries

# Téléchargeur
downloader = FileDownloader()
downloader.batch_download(urls)
```

## 📝 Exemples

### Obtenir des statistiques

```python
from src.scraper import DNBScraper

scraper = DNBScraper()
scraper.run_scraping()
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
scraper.run_scraping()

# Filtrer 2024
entries_2024 = [e for e in scraper.structured_entries
                if e.session.value.startswith('2024')]

urls_2024 = [f.download_url for entry in entries_2024 for f in entry.files]

downloader = FileDownloader()
results = downloader.batch_download(urls=urls_2024)
```

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

## ⚙️ Configuration

### Variables d'environnement (optionnel)

Créez un fichier `.env` pour personnaliser :

```env
# Principales options
SELENIUM_HEADLESS=True         # Mode headless
MAX_WORKERS=5                  # Téléchargements concurrents
LOG_LEVEL=INFO                 # Niveau de log
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

## 🗂️ Structure du projet

```
sokratika-ExamScrapper/
│
├── src/                        # Code source principal
│   ├── __init__.py            # Initialisation du package
│   ├── scraper.py             # Module de scraping (DNBScraper)
│   ├── downloader.py          # Module de téléchargement (FileDownloader)
│   ├── parser.py              # Analyseur de métadonnées (MetadataParser)
│   └── utils.py               # Fonctions utilitaires
│
├── config/                    # Configuration
│   └── settings.py            # Paramètres de configuration
│
├── data/                      # Données téléchargées
│   ├── raw/                   # Fichiers téléchargés (organisés par matière)
│   │   ├── FR_DICTEE/         # Français - Dictée
│   │   │   ├── 5_NORMAL_FR_DICTEE_GENERALE_METROPOLE_63118/
│   │   │   │   └── 24-GENFRDAME1 BA/  # Dossier extrait (2024)
│   │   │   └── 122_NORMAL_FR_DICTEE_GENERALE_METROPOLE_54414/
│   │   │       └── 23-GENFRDAME1 BA/  # Dossier extrait (2023)
│   │   ├── FR_GRAM_COMP/      # Français - Grammaire/Compréhension
│   │   ├── MATHS/             # Mathématiques
│   │   ├── HIST_GEO_EMC/      # Histoire-Géographie-EMC
│   │   ├── SCIENCES/          # Sciences
│   │   └── LV_*/              # Langues Vivantes (Allemand, Anglais, etc.)
│   └── metadata/              # Fichiers JSON avec métadonnées
│
├── logs/                      # Fichiers de logs
│   ├── dnb_scraper_YYYY-MM-DD.log  # Log complet avec rotation
│   └── errors_only.log             # Log des erreurs uniquement
│
├── main.py                    # Point d'entrée CLI
├── requirements.txt           # Dépendances Python
├── setup.py                   # Configuration du package
└── README.md                  # Ce fichier
```

## 🛡️ Bonnes pratiques

- **Respect du serveur** : Rate limiting, retry automatique
- **Logging complet** : Logs avec rotation + log d'erreurs séparé (`errors_only.log`)
- **Code qualité** : Type hints, docstrings, gestion d'erreurs

## ⚖️ Licence

MIT License - Voir le fichier `LICENSE` pour plus de détails.

## ⚠️ Disclaimer

Ce projet est destiné à un usage éducatif et respecte les conditions d'utilisation du site eduscol.education.fr.
