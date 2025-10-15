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
- ✅ **Gestion d'erreurs robuste** avec retry automatique
- ✅ **Rate limiting** pour respecter le serveur
- ✅ **Logging complet** avec rotation de fichiers
- ✅ **Interface CLI** intuitive
- ✅ **Mode headless** ou visible pour le debugging

## 📋 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- **Google Chrome** (navigateur)
- **ChromeDriver** (compatible avec votre version de Chrome)
- Connexion Internet

### Installation de ChromeDriver

**Méthode 1 - Automatique (recommandé):**
ChromeDriver sera géré automatiquement par Selenium 4.15+

**Méthode 2 - Manuelle:**
1. Vérifiez votre version de Chrome : `chrome://version`
2. Téléchargez ChromeDriver correspondant : https://chromedriver.chromium.org/downloads
3. Ajoutez ChromeDriver au PATH système ou placez-le dans le dossier du projet

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

**Note**: Selenium sera installé automatiquement. Assurez-vous que Chrome est installé sur votre système.

## 📖 Utilisation

### Interface en ligne de commande (CLI)

Le projet fournit trois commandes principales :

#### 1. Lister les années et matières disponibles

```bash
python main.py list

# Optionnel: lister et lancer une validation des valeurs (enums)
python main.py list --validate

# Limiter le nombre de pages parcourues (ex: 2 premières pages)
python main.py list -p 2
```

Affiche toutes les années et matières disponibles avec le nombre de fichiers pour chacune.

#### 2. Scraper sans télécharger

```bash
# Extraire tous les liens PDF
python main.py scrape

# Sauvegarder les liens dans un fichier
python main.py scrape --output links.txt

# Limiter à N pages (ex: 3)
python main.py scrape -p 3
```

#### 3. Télécharger les PDFs

```bash
# Télécharger tous les PDFs
python main.py download

# Télécharger avec 10 workers concurrents
python main.py download --workers 10

# Télécharger dans un répertoire personnalisé
python main.py download --output-dir ./mes_pdfs

# Forcer le re-téléchargement des fichiers existants
python main.py download --force

# Désactiver l'organisation par année/matière
python main.py download --no-organize

# Limiter à 2 pages
python main.py download -p 2
```

#### 4. Valider les valeurs scrapées (enums) et générer un CSV

```bash
# Lance un parcours complet des pages et vérifie les colonnes suivantes :
#   - Session, Discipline, Série, Localisation
# Produit un fichier validation_report.csv avec colonnes :
#   Colonne | Valeur_Détectée | Enum_Value | Status (OK/MISSING)
python main.py validate

# Limiter à 2 pages pour la validation
python main.py validate -p 2
```

### Utilisation programmatique

```python
from src.scraper import DNBScraper
from src.downloader import PDFDownloader
from src.parser import MetadataParser

# Initialisation du scraper (headless par défaut)
scraper = DNBScraper()

# Ou en mode visible pour debugging
# scraper = DNBScraper(headless=False)

# Extraction des liens PDF (toutes les pages automatiquement)
pdf_links = scraper.extract_pdf_links()
print(f"Trouvé {len(pdf_links)} PDFs sur toutes les pages")

# Obtenir le résumé
summary = scraper.get_summary_dict()
print(f"Années disponibles: {summary['years']}")
print(f"Matières disponibles: {summary['subjects']}")

# Parser les métadonnées d'un lien
parser = MetadataParser()
for link_data in pdf_links[:5]:  # Premiers 5 liens
    metadata = parser.parse_url(
        link_data['url'], 
        link_data.get('data_atl_name')
    )
    print(f"Fichier: {metadata['filename']}")
    print(f"Année: {metadata['year']}")
    print(f"Matière: {metadata['subject']}")
    print(f"Type: {metadata['document_type']}")
    print()

# Téléchargement
urls = [link_data['url'] for link_data in pdf_links]
downloader = PDFDownloader(output_dir="data/raw")
results = downloader.batch_download(
    urls=urls,
    max_workers=5
)

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
│   ├── raw/                   # PDFs téléchargés (organisés par année/matière)
│   └── metadata/              # Fichiers JSON avec métadonnées
│
├── logs/                      # Fichiers de logs
│
├── tests/                     # Tests (vide dans version simplifiée)
│
├── main.py                    # Point d'entrée CLI
├── requirements.txt           # Dépendances Python
├── setup.py                   # Configuration du package
└── README.md                  # Ce fichier
```

## 📊 Structure HTML du site

Le scraper utilise **Selenium WebDriver** pour gérer la pagination JavaScript et extraire les liens de toutes les pages.

### Pagination :
- **Boutons de navigation** : Premier, Précédent, [1][2][3]..., Suivant, Dernier
- **Navigation automatique** : Parcourt toutes les pages jusqu'à la dernière avec le bouton "Suivant"
- **JavaScript click** : Utilise JavaScript pour éviter les interceptions d'éléments

### Structure du tableau :

```html
<table>
  <tbody>
    <tr>
      <td>Session</td>
      <td>Discipline</td>
      <td>Série</td>
      <td>Localisation</td>
      <td class="views-field-link">
        <a href="/document/[ID]/download" data-atl-name="24genfrdag1_v11.pdf|63414">
          Télécharger
        </a>
      </td>
    </tr>
  </tbody>
</table>
```

### Éléments clés :
- **Liens** : Format `/document/[ID]/download` (pas `.pdf`)
- **Métadonnées** : Attribut `data-atl-name` contenant `"filename.pdf|file_id"`
- **Colonnes** : Session, Discipline, Série, Localisation, Liens
- **Pagination** : Gérée dynamiquement avec JavaScript

## 📊 Métadonnées extraites

Le parser extrait automatiquement les informations depuis `data-atl-name` et les noms de fichiers :

- **Année** : Année de l'examen (ex: "2024" depuis "24genfrdag1_v11.pdf")
- **Matière** : Mathématiques, Français, Histoire-Géographie, Sciences, etc.
- **Session** : normale, remplacement
- **Série** : générale, professionnelle
- **Type de document** : sujet ou correction
- **URL** : Lien de téléchargement
- **Nom de fichier** : Nom extrait du data-atl-name
- **ID du fichier** : ID numérique du document

### Exemple de parsing :

```python
# data-atl-name: "24genfrdag1_v11.pdf|63414"
{
    'filename': '24genfrdag1_v11.pdf',
    'file_id': '63414',
    'year': '2024',           # "24" → "2024"
    'subject': 'Français',    # "fr" détecté
    'series': 'generale',     # "gen" détecté
    'document_type': 'sujet',
    'is_correction': False,
    'url': 'https://eduscol.education.fr/document/123/download'
}
```

## ⚙️ Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine du projet :

```env
# Selenium settings
SELENIUM_HEADLESS=True         # Mode headless (True) ou visible (False)
SELENIUM_TIMEOUT=20            # Timeout pour les éléments (secondes)
SELENIUM_PAGE_LOAD_WAIT=2.0    # Attente entre les pages (secondes)

# Rate limiting
REQUEST_DELAY=1.5              # Délai entre les requêtes (secondes)
DOWNLOAD_TIMEOUT=30            # Timeout de téléchargement (secondes)
MAX_RETRIES=3                  # Nombre de tentatives en cas d'échec

# Download settings
MAX_WORKERS=5                  # Nombre de téléchargements concurrents
VERIFY_SSL=True                # Vérifier les certificats SSL

# Organization
ORGANIZE_BY_YEAR=True          # Organiser par année
ORGANIZE_BY_SUBJECT=True       # Organiser par matière

# Logging
LOG_LEVEL=INFO                 # Niveau de log (DEBUG, INFO, WARNING, ERROR)
```

### Personnalisation dans `config/settings.py`

Vous pouvez modifier les paramètres directement dans `config/settings.py` :

- URL de scraping
- Headers HTTP
- Mapping des matières
- Chemins des fichiers

## 📁 Organisation des fichiers

Les PDFs téléchargés sont automatiquement organisés :

```
data/raw/
├── 2024/
│   ├── Français/
│   │   ├── 24genfrdag1_v11.pdf
│   │   └── 24genfrdag1_corrige.pdf
│   ├── Mathématiques/
│   │   ├── 24genmathag1_v11.pdf
│   │   └── 24genmathag1_corrige.pdf
│   └── Histoire-Géographie/
│       └── 24genhisgeoag1_v11.pdf
└── 2023/
    └── ...
```

## 🛡️ Bonnes pratiques implémentées

### Respect du serveur
- Rate limiting (délai configurable entre requêtes)
- User-Agent approprié
- Gestion des erreurs HTTP
- Retry avec backoff exponentiel

### Qualité du code
- Type hints (PEP 484)
- Docstrings Google style
- Conforme PEP 8
- Gestion d'erreurs complète

### Logging
- Logging structuré avec Loguru
- Rotation automatique des fichiers de log
- Niveaux de log configurables
- Logs colorés dans la console

## 🔧 API Simplifiée

### DNBScraper

```python
class DNBScraper:
    def __init__(self, base_url: str = BASE_URL, headless: bool = True)
    def extract_pdf_links(self, url: Optional[str] = None, max_pages: Optional[int] = None) -> List[Dict[str, str]]
    def get_summary_dict(self) -> Dict
    def close(self) -> None  # Ferme le WebDriver
    def extract_distinct_table_values(self) -> Dict[str, Set[str]]  # valeurs par page
    # Après extraction, les entrées structurées par ligne sont disponibles:
    # scraper.structured_entries: List[ExamEntry]
```

**Nouvelles fonctionnalités :**
- Mode headless (navigateur invisible) par défaut
- Pagination automatique (parcourt toutes les pages avec JavaScript click)
- Fermeture automatique des overlays/modals
- Waits explicites pour une meilleure stabilité

### MetadataParser

```python
class MetadataParser:
    def __init__(self)
    def parse_url(self, url: str, data_atl_name: Optional[str] = None) -> Dict[str, Optional[str]]
```

### PDFDownloader

```python
class PDFDownloader:
    def __init__(self, output_dir: Path = RAW_DATA_DIR)
    def batch_download(self, urls: List[str], metadata: Optional[Dict] = None, 
                      max_workers: int = MAX_WORKERS, skip_existing: bool = True,
                      organize: bool = True) -> Dict[str, List]
```

## 🐛 Dépannage

### ChromeDriver not found

```bash
# Vérifier que Chrome est installé
# Windows: Vérifier dans "Programmes et fonctionnalités"
# Linux: google-chrome --version
# Mac: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# Selenium 4.15+ gère ChromeDriver automatiquement
# Si problème persiste, installez webdriver-manager:
pip install webdriver-manager
```

### Erreur "WebDriver initialization failed"

```bash
# Vérifier la version de Chrome et Selenium
pip install --upgrade selenium

# Ou utiliser le mode visible pour déboguer
# Dans votre code: scraper = DNBScraper(headless=False)
```

### Timeout lors de la pagination

```bash
# Augmenter les timeouts dans .env
echo "SELENIUM_TIMEOUT=30" >> .env
echo "SELENIUM_PAGE_LOAD_WAIT=3.0" >> .env
```

### Erreur de connexion

```bash
# Vérifier la connectivité
python -c "import requests; print(requests.get('https://eduscol.education.fr').status_code)"
```

### Problèmes de SSL

```bash
# Désactiver la vérification SSL (non recommandé)
echo "VERIFY_SSL=False" >> .env
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

print(f"Total PDFs: {stats['total']}")
print(f"Années disponibles: {stats['years']}")
print(f"Matières disponibles: {stats['subjects']}")
print(f"Sujets: {stats['by_type']['sujet']}")
print(f"Corrections: {stats['by_type']['correction']}")
```

### Télécharger uniquement les PDFs de 2024

```python
from src.scraper import DNBScraper
from src.downloader import PDFDownloader
from src.parser import MetadataParser

scraper = DNBScraper()
pdf_links = scraper.extract_pdf_links()

parser = MetadataParser()
links_2024 = []

for link_data in pdf_links:
    metadata = parser.parse_url(link_data['url'], link_data.get('data_atl_name'))
    if metadata['year'] == '2024':
        links_2024.append(link_data['url'])

print(f"Trouvé {len(links_2024)} PDFs pour 2024")

downloader = PDFDownloader()
results = downloader.batch_download(links_2024)
```

## ⚖️ Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## ⚠️ Disclaimer

Ce projet est destiné à un usage éducatif et respecte les conditions d'utilisation du site eduscol.education.fr. Les utilisateurs sont responsables de l'utilisation qu'ils font de cet outil et doivent respecter les bonnes pratiques de web scraping éthique.

## 👥 Auteurs

- **Sokratika** - *Développement initial* - [taieb1919](https://github.com/taieb1919)

## 🙏 Remerciements

- Ministère de l'Éducation nationale pour la mise à disposition des annales
- Communauté Python pour les excellentes bibliothèques

## 📧 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur GitHub.

---

**Note** : Ce projet scrape des documents publics mis à disposition par le ministère de l'Éducation nationale français. Utilisez-le de manière responsable et respectueuse.
