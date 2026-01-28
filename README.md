# Pactown Live Debug 🚀

Real-time Bash script analyzer and auto-fixer with ShellCheck integration.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)
![ShellCheck](https://img.shields.io/badge/ShellCheck-integrated-orange.svg)

## Features

- ⚡ **Real-time analysis** - Błędy widoczne podczas pisania
- 🔧 **Auto-fix** - Automatyczne naprawianie typowych błędów
- 📜 **Historia zmian** - Pełna historia wykrytych błędów i poprawek
- 💾 **Download** - Pobieranie poprawionego skryptu
- 🐳 **Docker** - Łatwe uruchomienie w kontenerze

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

## Struktura projektu

```
pactown-live-debug/
├── app/
│   └── index.html      # Frontend application
├── server.py           # Python backend server
├── Dockerfile          # Container definition
├── docker-compose.yml  # Docker Compose config
└── README.md          # This file
```

## Rozwój

### Roadmap

- [ ] Wsparcie dla Python/Node.js
- [ ] AI-powered explanations (llama.cpp)
- [ ] Collaborative debugging
- [ ] VSCode extension

### Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License

MIT License - Softreck © 2026

---

*Część projektu [Pactown](https://pactown.dev) - Platforma edukacyjna dla juniorów*
