dota2-api-pipeline-data/
  services/
    ingestion/
      pyproject.toml        # або requirements.txt
      requirements.txt
      requirements-dev.txt
      __init__.py

      app/
        __init__.py
        main.py             # FastAPI / health / orchestration

      providers/            # 👈 все, що знає про формати зовнішніх API
        __init__.py

        opendota/
          __init__.py
          client.py         # HTTP клієнт
          adapters.py       # OpenDota JSON -> domain contract
          fixtures/
            match_full_real.json
            match_minimal.json

        dotabuff/
          __init__.py
          adapters.py
          fixtures/

        stratz/
          __init__.py
          adapters.py
          fixtures/

      domains/              # 👈 твій внутрішній контракт (НЕ знає про API формат)
        __init__.py

        matches/
          __init__.py
          dtos.py
          parsers.py
          fixtures/
            minimal.json

        players/
          __init__.py
          dtos.py
          parsers.py
          fixtures/
            minimal.json

        draft/
          __init__.py
          dtos.py
          parsers.py
          fixtures/
            minimal.json

      tests/
        __init__.py

        providers/
          test_opendota_adapter.py

        domains/
          test_matches_parser.py
          test_players_parser.py