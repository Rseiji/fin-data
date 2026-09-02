# Roadmap

Ideias e melhorias futuras para o `fin-data`. Sem compromisso de prazo — apenas um lugar para anotar pensamentos.

## Ideias

- [x] Aprimorar Logging. Execuções demoradas devem, ao menos, registrar algo em console para que facilite o tracking da execução
- [ ] Aprimorar performance da execução. Custo de tempo tem sido alto até mesmo para atualização dos tickers já existentes
- [ ] Fragmentar tabelas: contamos com uma tabela única para a ingestão de todos os tipos de série histórica, a despeito de tipo.
      Poderia haver uma para índice, outra para ações brasileiras, e assim por diante.
- [ ] CICD
- [ ] Implementação em Cloud: Host database, API. Disponibilizar como serviço interno para alimentar outros projetos pessoais
- [ ] Mecanismo de retry/backoff
- [ ] Mecanismos de validação de dados
- [x] Adicionar endpoint de status, para saber metadados a respeito de uma determinada série histórica
- [ ] Health check dos dados. Identificar ativos cuja última atualização esteja muito atrasada.
- [ ] Cache da API. Evitar consultas repetitivas ao banco para dados frequentemente solicitados (caso escale ou para fins didáticos apenas)
- [ ] API - aprimorar fluxo de versionamento e documentação
- [ ] Backup do database (após migração para cloud)
- [ ] UI para acompanhamento geral dos status dos dados ingeridos
- [ ] Aprimorar o README.md e a pasta docs/


## Em consideração

## Descartadas
