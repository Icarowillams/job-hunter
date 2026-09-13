# Job Hunter Inteligente

Sistema pessoal de monitoramento, análise e notificação de vagas de emprego.

O objetivo do projeto é reduzir o trabalho manual de procurar vagas, permitindo que o sistema busque oportunidades, analise a compatibilidade com o perfil profissional e envie notificações sobre vagas relevantes.

## Objetivo

O Job Hunter Inteligente foi desenvolvido para uso pessoal, com foco em vagas compatíveis com o perfil do candidato.

O fluxo principal do sistema é:

1. Carregar o perfil profissional do candidato.
2. Buscar vagas utilizando a SerpAPI.
3. Persistir as vagas encontradas.
4. Extrair os requisitos das vagas.
5. Analisar a compatibilidade entre candidato e vaga.
6. Persistir os resultados da análise.
7. Enviar notificações por e-mail para vagas compatíveis.
8. Registrar a execução do pipeline e suas métricas.

## Estado atual

O projeto possui uma estrutura modular organizada por responsabilidades:

* Domain
* Ingestion
* Extraction
* Matching
* Scoring
* Analysis
* Pipeline
* Application
* Infrastructure
* Notifications
* Retry
* Metrics
* SQLite persistence

O fluxo principal atualmente executa uma coleta e análise por meio do método `run_once()`.

## Arquitetura

```text
src/
├── main.py
├── analysis/
│   └── job_analyzer.py
├── application/
│   ├── bootstrap.py
│   ├── orchestrator.py
│   ├── metrics/
│   ├── notification/
│   ├── retry/
│   ├── scheduler/
│   └── shutdown/
├── domain/
│   ├── enums.py
│   ├── metric.py
│   ├── models.py
│   └── notification.py
├── extraction/
│   ├── requirement_extractor.py
│   └── skill_normalizer.py
├── infrastructure/
│   ├── candidate_profile_repository.py
│   ├── database.py
│   ├── email_notifier.py
│   ├── job_analysis_repository.py
│   ├── job_repository.py
│   ├── job_requirement_repository.py
│   ├── metric_repository.py
│   ├── notification_repository.py
│   ├── pipeline_execution_repository.py
│   ├── profile_loader.py
│   └── smtp_client.py
├── ingestion/
│   └── collectors/
│       ├── fallback_job_collector.py
│       ├── job_collector.py
│       ├── serpapi_google_search_collector.py
│       └── serpapi_job_collector.py
├── matching/
│   └── requirement_matcher.py
├── pipeline/
│   └── analysis_pipeline.py
└── scoring/
    └── scoring_engine.py
```

## Tecnologias

* Python 3.11+
* Pydantic
* Pydantic Settings
* Requests
* HTTPX
* PyYAML
* Python Dotenv
* Pytest
* SQLite
* Poetry

## Requisitos

Antes de executar o projeto, tenha instalado:

* Python 3.11 ou superior
* Poetry
* Uma chave da SerpAPI
* Uma conta de e-mail com acesso SMTP
* Uma senha de aplicativo caso o provedor de e-mail exija autenticação por senha de aplicativo

## Instalação

Clone o repositório:

```bash
git clone https://github.com/Icarowillams/job-hunter.git
cd job-hunter
```

Instale as dependências:

```bash
poetry install
```

Entre no ambiente virtual do Poetry:

```bash
poetry shell
```

## Configuração

Crie o arquivo `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis necessárias:

```env
SERPAPI_API_KEY=your_serpapi_key_here

EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=your_email@gmail.com
```

As variáveis relacionadas ao Telegram estão presentes no `.env.example`, mas o fluxo atual de inicialização utiliza o notifier de e-mail.

## Perfil do candidato

O caminho padrão do perfil é:

```text
data/profile.json
```

Esse caminho é definido no `config.yaml`:

```yaml
paths:
  profile: "data/profile.json"
```

O perfil é carregado durante a inicialização da aplicação e persistido no banco de dados.

## Configuração da coleta

A fonte configurada atualmente é a SerpAPI:

```yaml
source: serpapi

serpapi:
  api_key: ${SERPAPI_API_KEY}
  query_params:
    location: "Brazil"
    query: "desenvolvedor backend junior OR backend developer junior OR desenvolvedor full stack junior OR full stack developer junior OR node.js developer junior OR typescript developer junior"
    limit: 20
```

A consulta busca principalmente oportunidades relacionadas a:

* Backend Júnior
* Desenvolvimento Backend
* Desenvolvimento Full Stack Júnior
* Node.js
* TypeScript

O limite padrão configurado é de 20 vagas por coleta.

## Configuração de análise e pontuação

A configuração atual utiliza os seguintes pesos:

```yaml
scoring:
  weights:
    role_fit: 0.20
    seniority_fit: 0.15
    technical_fit: 0.40
    experience_fit: 0.15
    semantic_fit: 0.10
```

Os critérios considerados incluem:

* Compatibilidade com a função
* Compatibilidade de senioridade
* Compatibilidade técnica
* Compatibilidade de experiência
* Compatibilidade semântica

## Notificações por e-mail

As notificações são habilitadas no `config.yaml`:

```yaml
notification:
  enabled: true
  minimum_score: 70
  channel: email
```

Uma vaga pode gerar notificação quando:

* A análise foi concluída com sucesso.
* A pontuação de compatibilidade é maior ou igual a `70`.
* A análise não identificou um bloqueador rígido (`hard_blocker`).
* O notifier está configurado e habilitado.

A configuração SMTP está definida na seção `email`:

```yaml
email:
  smtp_server: ${EMAIL_SMTP_SERVER}
  smtp_port: 587
  username: ${EMAIL_USERNAME}
  password: ${EMAIL_PASSWORD}
  from: ${EMAIL_FROM}
  to: ${EMAIL_TO}
```

O envio possui política opcional de retry:

```yaml
notification:
  retry:
    enabled: true
    max_attempts: 3
    delay_seconds: 2
    backoff_multiplier: 2
```

## Persistência

O sistema utiliza SQLite.

Banco padrão:

```text
data/job_hunter.db
```

O caminho pode ser alterado no `config.yaml`:

```yaml
paths:
  db: "data/job_hunter.db"
```

A aplicação possui repositórios para persistir:

* Perfil do candidato
* Vagas
* Requisitos das vagas
* Análises de compatibilidade
* Execuções do pipeline
* Notificações
* Métricas

## Execução

O ponto de entrada está em:

```text
src/main.py
```

O comando principal executa uma única rodada do sistema:

```python
runner = build_application()
return runner.run_once()
```

Para executar:

```bash
python -m src.main
```

A execução realiza a coleta, processamento, análise, persistência e possíveis notificações das vagas encontradas.

## Resultado da execução

O orquestrador retorna um `RunResult` contendo:

* Total de vagas encontradas
* Total de vagas processadas
* Total de processamentos bem-sucedidos
* Total de processamentos com falha
* Total de notificações enviadas
* Resultados individuais por vaga
* Lista de erros encontrados

Cada resultado individual pode conter:

* ID da vaga
* Título da vaga
* Status do processamento
* Pontuação de compatibilidade
* Indicação de bloqueador rígido
* Status da notificação
* Erros de processamento
* Erros de notificação

## Testes

Execute todos os testes com:

```bash
python -m pytest -v
```

Para executar os testes com cobertura:

```bash
python -m pytest --cov=src --cov-report=term-missing
```

## Qualidade de código

As ferramentas de desenvolvimento configuradas incluem:

```bash
black .
isort .
flake8 .
mypy src
```

## Configurações adicionais

O `config.yaml` possui configurações para:

* Scheduler
* Graceful shutdown
* Métricas
* Logging
* Embeddings
* Retry de notificações

Entretanto, o ponto de entrada atual utiliza diretamente `run_once()`. Portanto, as configurações de scheduler e execução recorrente não devem ser consideradas ativas no fluxo principal até que sejam conectadas ao processo de inicialização da aplicação.

## Limitações atuais

* A execução principal ocorre uma única vez.
* O notifier configurado no bootstrap é o de e-mail.
* A configuração do Telegram ainda não está conectada ao fluxo principal de notificações.
* O scheduler está presente na estrutura do projeto, mas não é iniciado pelo `src/main.py` atual.
* A fonte principal de coleta é a SerpAPI.
* O fallback de coleta não é ativado automaticamente pelo bootstrap atual quando a chave da SerpAPI está ausente; nesse caso, é utilizado um coletor nulo que retorna uma lista vazia.

## Próximos passos

Possíveis evoluções para o uso pessoal:

* Melhorar as consultas de vagas.
* Ajustar os filtros para vagas de Java, Spring Boot, Node.js e TypeScript.
* Melhorar a deduplicação de vagas.
* Conectar o scheduler ao ponto de entrada.
* Implementar notificações via Telegram.
* Melhorar a visualização das análises.
* Adicionar acompanhamento do status das candidaturas.
* Melhorar o tratamento de vagas expiradas ou sem data.
* Criar relatórios das vagas mais compatíveis.
* Evoluir os testes de integração.

## Licença

Projeto pessoal desenvolvido por Ícaro.
