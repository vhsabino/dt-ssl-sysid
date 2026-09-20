# Notas de refatoração — ETL dos logs (`dtssl.data.{recordio,_proto,extract,rotate,cli}`)

*Refatoração de 02/09/2026 (SPEC §2/§4.7). Código e identificadores em EN; estas notas em PT-BR.*

## 1. O que foi migrado para onde

| Antes (legado) | Depois (`src/dtssl/data/`) | Observação |
|---|---|---|
| `python/pyrecordio/pyrecordio/compressed_proto_record_reader.py` | `recordio.py` — `iter_records`, `read_records`, `count_records`, `write_records`, `pack_record`, `ReadStats` | leitor **e escritor** puro-Python do container; sem dependência de protobuf |
| `python/proto/proto/generated/{RCLog,RoboCupSSL}.py` (betterproto) + `python/utils/utils/auto_generate_proto.py` | `_proto/` — `rc_log.proto`, `ssl_gc_{referee_message,game_event,geometry}.proto` (cópias verbatim do ssl-unification) + `*_pb2.py` gerados e versionados + `build_proto.py` + camada de acesso em `__init__.py` (`decode_log`, `encode_log`, `new_log`, `processed_frame`, `raw_frames`, `robot_commands`, `telemetries`, `referee`, `raw_referee`, `has_field`) | **betterproto não é mais necessário** (nem `protoc` em runtime). A visão (`ssl_vision_*`) e `ssl_gc_common` são importadas de `dtssl.bridge.proto` (cada `.proto` só pode ser registrado uma vez no pool de descritores do processo) |
| `python/data_select/data_select/data_filter_operator.py` + `python/utils/utils/utils.py` (`LogFields`, `gel_2d_length_in_column`) + `notebooks/01_logExtractor.ipynb` | `extract.py` — `extract_streams`, `extract_raw_streams`, `normalize_streams`, `write_dataset`, `read_dataset`, `read_manifest`, `inspect_log`, `dataset_name_from_log` | porta fiel do notebook 01 (ver §3) |
| `notebooks/02_splitByLabels.ipynb` | `extract.py` — `ANNOTATIONS`, `annotations_frame`, `chunk_intervals`, `validate_intervals`, `split_dataset`, `split_by_labels` | porta fiel do notebook 02; as 20 anotações do log `2026-05-18_19-2-15` (antes hard-coded no notebook) vivem em `extract.ANNOTATIONS` |
| `scripts/build_rotate_splits.py` | `rotate.py` — `demux_rotate_raw`, `build_event_tables`, `write_tables`, `write_metadata`, `build_rotate_splits`, `load_robot_geometry`, `GeometryConstants` | mesma lógica; geometria lida de `config/robot_geometry.json` via `dtssl.paths.config_path` (quando `dtssl.config`/`geometry` existirem, trocar `load_robot_geometry`) |
| `scripts/build_rotate_qc.py` | `rotate.py` — `rotate_qc` | texto do relatório mantido verbatim (é registro histórico D9); links das figuras relativos ao diretório do `.md` |
| — | `cli.py` — `register(subparsers)`, `main()` | `dtssl etl extract|split|rotate|inspect` (ver §2) |
| `python/kinematics.py` (ScriptNode Isaac com K antiga, `k*_3 = 3.324525253`) | **removido** (sem consumidor; constantes deprecated já documentadas em `config/robot_geometry.json:scan_2026-07-24.python_kinematics_py`; substituído por `dtssl.kinematics`) | |

Removidos do repositório: `python/` (inteiro) e `scripts/build_rotate_{splits,qc}.py`. Os dois notebooks foram
**substituídos por versões finas** (documentos executáveis que só chamam `dtssl.data.extract`; saídas limpas).

Novos testes: `tests/test_etl_recordio.py` (10), `tests/test_etl_extract.py` (18, 1 só roda com log real),
`tests/test_etl_rotate.py` (7), `tests/test_etl_cli.py` (3). Todos rodam sem dataset (log sintético de 100 quadros,
2 robôs aliados + 1 inimigo, gerado com o próprio escritor + `_proto`); o teste
`test_chunk_intervals_match_frozen_labels_manifest` (`requires_data`) confere **bit a bit** os 46 chunks contra
`data/extracted/2026-05-18_19-2-15/splits/labels_manifest.csv`.

## 2. Como rodar

```bash
pip install -e .                      # numpy, pandas, pyarrow, protobuf (>= 4.21); nada de betterproto/protoc
dtssl etl inspect logs/2026-05-18_19-2-15.log.gz                       # contagens por stream, duração, registros corrompidos
dtssl etl extract logs/2026-05-18_19-2-15.log.gz data/extracted/2026-05-18_19-2-15 [--csv] [--max-records N]
dtssl etl split   data/extracted/2026-05-18_19-2-15 [labels.csv] [--chunk-s 10] [--out DIR] [--csv]
dtssl etl rotate  data/extracted/2026-05-18_19-2-15/splits/rotate/rotate_raw.csv \
                  data/extracted/2026-05-18_19-2-15/splits/rotate [--qc] [--pad-s 0.2] [--csv]
python -m dtssl.data.cli ...          # o mesmo, sem o entry point `dtssl` (enquanto `dtssl.cli` não integra `register`)
```

Em Python:

```python
from dtssl.data.extract import extract_streams, write_dataset, split_by_labels
streams = extract_streams("logs/2026-05-18_19-2-15.log.gz")      # dict de 7 DataFrames + .meta (timeref_ns, contadores)
write_dataset(streams, "data/extracted/2026-05-18_19-2-15")       # parquet + manifest.json
split_by_labels("data/extracted/2026-05-18_19-2-15")               # anotações embutidas; ou labels.csv (label,t_start,t_end)
from dtssl.data.rotate import build_rotate_splits
build_rotate_splits("…/rotate_raw.csv", "…/splits/rotate", qc=True)
```

`labels.csv` = anotações brutas (`label,t_start,t_end`, segundos a partir de `t=0` do log); `split` sem
argumento usa `extract.ANNOTATIONS[<nome do diretório>]` (só `2026-05-18_19-2-15`).

Regenerar os `*_pb2.py` (só quando o `.proto` do ssl-unification mudar):
`python -m dtssl.data._proto.build_proto [--sync <ssl-unification>/libs/protobufs/include/protobufs/pb/proto] [--check]`
(precisa de `grpcio-tools`; os arquivos versionados foram gerados com protoc 25.1 / grpcio-tools 1.62.3, iguais aos do
bridge; o pós-processamento remove a checagem de versão de gencode, então carregam em qualquer runtime protobuf ≥ 3.20).

Teste contra um log real (não há log no ambiente cloud; 300 MB+ no PC):
`DTSSL_TEST_LOG=C:\...\2026-05-18_19-2-15.log.gz [DTSSL_TEST_LOG_MANIFEST=<manifest.json do notebook>] pytest tests/test_etl_extract.py -k real_log`
— compara contagens/`t_start`/`t_end` por stream com o manifest do notebook e, se o dataset DVC estiver presente,
`square_01_01/commands.parquet` regenerado **igual** ao congelado (`assert_frame_equal`).

## 3. Formato do log (verificado em `libs/recordio/include/recordio.{h,cpp}` + `src/Modules/Logger/Logger.cpp`)

- Por registro: `int32 LE magic = 0x3ed7230a` · `uint64 LE uncompressed_size` · `uint64 LE compressed_size`
  (0 ⇒ payload cru) · payload = `zlib compress()` (RFC 1950) de um `RCLog.Log` serializado.
- O Logger abre o arquivo com `fopen(..., "a")` e nomeia `<data>.log.gz`: **não é gzip** (`gzip -d` falha). O leitor
  fareja `1f 8b` e aceita também um container realmente gzipado (`write_records(..., gzip_wrap=True)`).
- Robustez: registro com zlib corrompido/tamanho errado é pulado (como o `pyrecordio` legado); magic errado dispara
  ressincronização byte a byte no próximo magic (o legado pulava 20 bytes; o C++ aborta); cauda truncada (logger morto
  no meio da escrita) encerra a leitura sem erro. `strict=True` levanta `RecordIOError`. Contadores em `ReadStats`.
- `rc_log.proto` é proto2 com campos `required`; o parse é permissivo (campo `required` ausente ou enum desconhecido
  de versões mais novas do GC/ssl-vision não abortam). O betterproto do notebook também ignorava `required`.

## 4. Semântica reproduzida dos notebooks (e as poucas diferenças)

Regras idênticas ao notebook 01: linha só existe se a mensagem existe e `timestamp > 1` ns (`publish_timestamp`
de `processed_frame`/`raw_frame`/`navigation`, `receive_timestamp` da telemetria); `referee` exige
`game_state_name` não vazio; `timeref` = menor **primeiro** `timestamp` (em ordem de log, após o filtro) entre
`ball` e `raw_ball`; ns→s com `((ts - timeref) % 1e13) / 1e9` **em float64** (os epoch-ns ~1.78e18 têm resolução de
256 ns em float64 — a mesma perda de precisão do notebook, preservada de propósito; `manifest.timeref_ns` é o
mesmo float); `sort_values('timestamp')` (quicksort default, como o notebook) e `velocity_norm`/`acceleration_norm`
com `sqrt(x**2 + y**2)` do pandas. Colunas, ordem e dtypes iguais aos parquets congelados (`timestamp` float64,
`robot_id` int64, `team` string, `actuation_*`/`dribbler_ball_contact` bool, `count` int64).

Notebook 02: `chunk_intervals` (N = ⌈D/10⌉ chunks iguais, `source_idx` por label, `event_id` `<label>_<anot:02d>_<chunk:02d>`),
seleção `[t0, t1)`, `timestamp_event = timestamp - t_start` do chunk, `all_<stream>_labeled.parquet` com
`label/event_id/source_idx/chunk_idx`, `labels_manifest.csv` com `duration = t1 - t0`. Verificado bit a bit
contra o `labels_manifest.csv` congelado (lido com `float_precision="round_trip"`; o parser default do
`read_csv` erra 1 ulp).

Diferenças conscientes:

1. **CSV é opcional** (`--csv` / `csv=True`); o notebook gravava sempre `.csv` + `.parquet`. O parquet é a fonte
   consumida por MATLAB (`parquetread`) e pelo loader; o DVC só guarda parquet.
2. **Streams vazios** mantêm as colunas do contrato (tipadas) em memória e no `manifest.json` (`columns` não fica
   `[]`); o parquet continua não sendo gravado quando vazio (igual ao notebook).
3. `manifest.json` ganha um bloco extra `extraction` (`n_records`, `n_bad_records`, `n_resyncs`, `truncated`,
   `gzip_wrapped`, `dtssl_version`, `tool`); as chaves originais (`log_file`, `timeref_ns`, `tables`) são iguais.
4. Registros indecodificáveis: o notebook descartava o registro inteiro quando `betterproto.to_dict` levantava
   `IndexError` ("enum inválido"); o protobuf padrão não falha nesses casos, então um log com enums desconhecidos
   pode render **alguns registros a mais** do que a extração original. No log `2026-05-18_19-2-15` os totais do
   notebook (ball 27413, raw_ball 14150, processed_robots 27408, raw_robots 16131, commands 48012, telemetry
   57415, referee 27407) devem ser conferidos com `DTSSL_TEST_LOG_MANIFEST` na primeira execução no PC.
5. Empates de `timestamp` (vários robôs no mesmo quadro): a ordem relativa vem do quicksort do numpy da máquina;
   pode diferir entre versões de numpy (irrelevante para o loader, que filtra por `robot_id`).
6. `split` calcula e reporta (logging) os chunks fora do log e as sobreposições, em vez de imprimir com emojis; a
   checagem "< 30 amostras de bola" está no CLI (`dtssl etl split`) e no notebook fino.

## 5. Rotate (`rotate.py`)

- Funções puras em vez de script com `argparse` + estado global; `demux_rotate_raw` devolve um `RotateRaw`
  (streams, séries SG, segmentos) reutilizado por `build_rotate_splits` e `rotate_qc`.
- Geometria: `load_robot_geometry(source)` aceita dict, caminho ou `None` (= `config/robot_geometry.json`);
  `GeometryConstants.from_json` extrai R/r CAD, firmware, deprecated e a zona morta. O `metadata.json` de cada
  evento registra `geometry_source` e `tool`.
- Relatório de QC: mesmo conteúdo do `qc_rotate_20260724_125828.md` (texto D9 verbatim), figuras em
  `<dir do md>/figs/`, links relativos; `to_markdown` precisa de `tabulate` (fallback em texto puro).
- Não há `rotate_raw.csv` no ambiente cloud; o teste usa um CSV sintético (10 degraus de 2.5 s, robô yellow #6,
  zona morta em ±0.25/±0.5) e valida o layout, o contrato, `metadata.json`, o carregamento no loader e o QC.

## 6. Pendências / avisos

- `pyproject.toml` ainda declara o extra `etl = ["betterproto>=1.2.5"]`: pode ser removido (o ETL só usa
  `protobuf`, dependência básica) — não editado aqui (fora do escopo deste agente).
- `dtssl.cli` (entry point `dtssl`) precisa chamar `dtssl.data.cli.register(subparsers)`; até lá use
  `python -m dtssl.data.cli`.
- `src/dtssl/analysis/__init__.py` (docstring) ainda cita `scripts/build_rotate_splits.py`; apontar para
  `dtssl.data.rotate`. `DESIGN.md` e `reorganize.ps1` citam `python/` (legado, ambos marcados para remoção no SPEC).
- Anotações de outros logs: escrever `labels.csv` ou acrescentar a `extract.ANNOTATIONS` (com a data/fonte).
