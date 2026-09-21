# Roadmap

Ideias e melhorias futuras para o `fin-data`. Sem compromisso de prazo — apenas um lugar para anotar pensamentos.

## Prioridade alta

- [x] Separar liveness e readiness, validando a conectividade com o banco no readiness check
- [ ] Executar a ingestão de forma assíncrona, com recurso de acompanhar o status de cada execução
- [ ] Impedir execuções simultâneas do pipeline e garantir idempotência por execução
- [x] Adicionar paginação e limites máximos aos endpoints de histórico e resumo
- [ ] Remover detalhes de exceções internas das respostas HTTP e adicionar `request_id` para rastreamento
- [x] Adicionar testes de health com banco disponível e indisponível
- [x] Adicionar testes para paginação, limites e valores decimais iguais a zero

## Prioridade média

- [ ] Validar e normalizar símbolos, incluindo tamanho, formato, duplicidade e quantidade máxima por requisição
- [ ] Definir contrato explícito para timezone e limites inclusivos de `start` e `end`
- [ ] Tornar a seleção do último preço determinística quando houver múltiplas fontes
- [ ] Otimizar o endpoint de status para evitar consultas N+1 e carregar históricos inteiros em memória
- [ ] Migrar criação de tabelas em produção para migrações Alembic
- [ ] Adicionar autenticação e rate limiting ao endpoint de ingestão
- [ ] Adicionar métricas de requisições, scrapers, pipeline e atualização dos ativos
- [ ] Cobrir com testes datas inválidas, timezone, concorrência e não vazamento de erros internos

## Ideias

- [x] Aprimorar Logging. Execuções demoradas devem, ao menos, registrar algo em console para que facilite o tracking da execução
- [x] Adicionar endpoint de status, para saber metadados a respeito de uma determinada série histórica
- [ ] Aprimorar performance da execução. Custo de tempo tem sido alto até mesmo para atualização dos tickers já existentes
- [ ] Fragmentar tabelas: contamos com uma tabela única para a ingestão de todos os tipos de série histórica, a despeito de tipo.
      Poderia haver uma para índice, outra para ações brasileiras, e assim por diante.
- [ ] Cache da API. Evitar consultas repetitivas ao banco para dados frequentemente solicitados (caso escale ou para fins didáticos apenas)
- [ ] API - aprimorar fluxo de versionamento e documentação
- [ ] API - Autenticação
- [ ] CICD
- [ ] Implementação em Cloud: Host database, API. Disponibilizar como serviço interno para alimentar outros projetos pessoais
- [ ] Mecanismo de retry/backoff
- [ ] Mecanismos de validação de dados
- [ ] Health check dos dados. Identificar ativos cuja última atualização esteja muito atrasada.
- [ ] Backup do database (após migração para cloud)
- [ ] UI para acompanhamento geral dos status dos dados ingeridos
- [ ] Aprimorar o README.md e a pasta docs/
- [ ] Acoplar Harness ao repositório
- [x] Paginação na API


## Em consideração

- [x] Concorrência por fonte nas etapas de fetch para reduzir tempo total de ingestão
- [x] Persistência em lote (batch) para registros de bronze, evitando commits por item
- [x] Atualização incremental por símbolo com base no último timestamp/última data processada
- [x] Broadcast de requisições para APIs que suportem múltiplos ativos em uma única chamada
- [x] Reduzir lookback em atualizações normais, mantendo backfill como operação explícita
- [ ] Reusar conexões HTTP / reduzir overhead de requests repetitivos

## Descartadas
