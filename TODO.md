chcialbym dodatkowo testowac roznego typu pliki jak docker, SQl, itd, ktore wymagaja kontekstu, chodzi o mozliwosc generowania tego mock i wskazywac wady, naawet nie majac pewlnego srodowiska, tworzac maksymalna ilosc sorodowiska, jak wynika z tego pliku i wskazac bledy samej konfiguracji, pliku z DSL, konfiguracyjnego roznych formatow IaC, itd

popraw wygląd, niestety nie wykrywa wszystkich błedów
Jak w ciągu najszybszego czasu prztetsowac wszystkie te projekty examples/*/*?
Stworz testy e2e, i zaktualizuj projekt, aby szybko wsazywął błędy, syzbciej niż uruhcomienie debuggera live z konkretnego kodu, jak to zrobić?


# Instalacja
pip install -e pactfix-py

# Użycie
[faulty.py](examples/python/faulty.py)
python -m pactfix examples/python/faulty.py -o output.py --log-file log.json -v

[faulty.sh](examples/bash/faulty.sh)
python -m pactfix examples/bash/faulty.sh -o output.sh --log-file log.json -v
