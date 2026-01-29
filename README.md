# Pactown Live Debug 🚀

Multi-language code analyzer and auto-fixer with Docker sandbox testing support.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)
![ShellCheck](https://img.shields.io/badge/ShellCheck-integrated-orange.svg)

## Features

- ⚡ **Real-time analysis** - Błędy widoczne podczas pisania
- 🔧 **Auto-fix** - Automatyczne naprawianie typowych błędów
- 📜 **Historia zmian** - Pełna historia wykrytych błędów i poprawek
- 💾 **Download** - Pobieranie poprawionego skryptu
- 🐳 **Docker sandbox** - Testowanie poprawek w izolowanym środowisku
- 🧪 **Multi-language** - Wsparcie dla Bash, Python, Go, Node.js, Dockerfile i innych

## Quick Start

### Docker (zalecane)

```bash
# Zbuduj i uruchom
docker-compose up --build

# Lub bezpośrednio z Docker
docker build -t pactown-live-debug .
docker run -p 8080:8080 pactfix-live-debug
```

Otwórz http://localhost:8080 w przeglądarce.

### Bez Docker

```bash
# Wymagane: Python 3.10+ i ShellCheck
apt-get install shellcheck  # Ubuntu/Debian
brew install shellcheck     # macOS

# Uruchom serwer
python3 server.py
```

## Jak używać

1. **Wklej kod** - W lewym panelu wklej swój skrypt Bash
2. **Poczekaj na analizę** - Błędy są wykrywane automatycznie
3. **Zobacz poprawki** - Prawy panel pokazuje poprawiony kod z komentarzami
4. **Pobierz** - Kliknij "Pobierz" aby zapisać poprawiony skrypt

## Przykład

### Wejście (z błędem):
```bash
#!/usr/bin/bash
OUTPUT=/home/student/output-

for HOST in server{a,b}; do
    echo "$(ssh student@${HOST} hostname -f") >> ${OUTPUT}${HOST}
done
```

### Wyjście (poprawione):
```bash
#!/usr/bin/bash
OUTPUT=/home/student/output-

for HOST in server{a,b}; do
    echo "$(ssh student@${HOST} hostname -f)" >> ${OUTPUT}${HOST}  # ✅ NAPRAWIONO: Poprawiono pozycję cudzysłowu
done
```

## Wykrywane błędy

| Kod | Opis |
|-----|------|
| SC1073 | Błędy składni - brakujące cudzysłowy, nawiasy |
| SC2086 | Niecytowane zmienne |
| SC2006 | Użycie `` zamiast $() |
| SC2164 | cd bez obsługi błędów |
| SC2162 | read bez flagi -r |

## API

### POST /api/analyze

Analizuje kod Bash i zwraca wyniki.

**Request:**
```json
{
  "code": "#!/bin/bash\necho $VAR"
}
```

**Response:**
```json
{
  "originalCode": "#!/bin/bash\necho $VAR",
  "fixedCode": "#!/bin/bash\necho \"$VAR\"",
  "errors": [],
  "warnings": [
    {
      "line": 2,
      "column": 6,
      "code": "SC2086",
      "message": "Zmienna powinna być w cudzysłowach"
    }
  ],
  "fixes": [
    {
      "line": 2,
      "message": "Dodano cudzysłowy wokół zmiennej",
      "before": "echo $VAR",
      "after": "echo \"$VAR\""
    }
  ]
}
```

## Stack technologiczny

- **Frontend**: Vanilla JS, CSS Grid, CSS Variables
- **Backend**: Python 3.12, http.server
- **Analysis**: ShellCheck (z fallback do wbudowanej analizy)
- **Container**: Docker, Alpine-based

## Pactfix CLI 🛠️

Projekt zawiera również narzędzie CLI `pactfix` do analizy i automatycznego poprawiania kodu w wielu językach.

### Główne funkcje

- **Project-wide scanning** (`--path`) - Analiza całego projektu
- **Docker sandbox** (`--sandbox`) - Testowanie poprawek w kontenerze
- **Automated testing** (`--test`) - Uruchamianie testów w sandboxie
- **Multi-language support** - Bash, Python, Go, Node.js, Dockerfile, i inne

### Przykłady użycia

```bash
# Analiza i poprawa całego projektu
pactfix --path ./my-project

# Uruchomienie w Docker sandboxie
pactfix --path ./my-project --sandbox

# Sandbox z testami
pactfix --path ./my-project --sandbox --test

# Wstawianie komentarzy nad poprawkami
pactfix --path ./my-project --comment
```

### Testowanie sandboxów

Projekt zawiera zestaw projektów testowych w `pactfix-py/test-projects/`:

```bash
# Uruchomienie testów sandboxów
make test-sandbox

# Uruchomienie z testami w kontenerach
make test-sandbox-tests
```

Każdy projekt testowy ma `_fixtures/faulty/` z baseline'owym kodem, co zapewnia deterministyczne testowanie.

## Struktura projektu

```
pactown-debug/
├── app/
│   └── index.html      # Frontend application
├── server.py           # Python backend server
├── pactfix-py/         # Pactfix CLI tool
│   ├── pactfix/        # Main package
│   ├── test-projects/  # Test projects with fixtures
│   └── scripts/        # Test scripts
├── Dockerfile          # Container definition
├── docker-compose.yml  # Docker Compose config
├── Makefile           # Build and test targets
└── README.md          # This file
```

## Rozwój

### Roadmap

- [x] Wsparcie dla Python/Node.js/Go/Dockerfile
- [ ] AI-powered explanations (llama.cpp)
- [ ] Collaborative debugging
- [ ] VSCode extension
- [ ] Więcej reguł automatycznych poprawek

### Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

Apache 2.0 License - Softreck © 2026

---

*Część projektu [Pactown](https://pactown.dev) - Platforma edukacyjna dla juniorów*
