# Planning Documentation

## Overview
Esta pasta contém documentação de planejamento e arquitetura do projeto Cardápio Online. É mantida como histórico do desenvolvimento mas não é necessária para executar o projeto.

## Estrutura

### `/codebase/` - Documentação Técnica
- **ARCHITECTURE.md** - Arquitetura geral do projeto
- **STACK.md** - Stack tecnológico (Python/Django, PostgreSQL, etc.)
- **STRUCTURE.md** - Estrutura de pastas e módulos
- **CONVENTIONS.md** - Convenções de código
- **TESTING.md** - Estratégia de testes
- **CONCERNS.md** - Preocupações técnicas e trade-offs
- **INTEGRATIONS.md** - Integrações externas

### `/milestones/` - Roadmap por Versão
- **v1.0-REQUIREMENTS.md** / **v1.0-ROADMAP.md** - Milestone v1.0
- **v1.1-REQUIREMENTS.md** / **v1.1-ROADMAP.md** - Milestone v1.1

### `/phases/` - Histórico de Fases de Desenvolvimento
- **01-pagamento-pix-manual/** - Implementação de PIX manual
- **02-gest-o-de-chaves-pix/** - Gestão de chaves PIX
- **03-revis-o-manual-e-auditoria/** - Revisão manual e auditoria
- **04-status-visual-core/** - Status visual core

Cada fase contém: PLAN.md, RESEARCH.md, SUMMARY.md

### Root Files
- **ROADMAP.md** - Roadmap geral (source of truth)
- **REQUIREMENTS.md** - Requisitos gerais do projeto
- **PROJECT.md** - Overview do projeto
- **STATE.md** - Estado atual do desenvolvimento
- **RETROSPECTIVE.md** - Retrospectiva e aprendizados

### `/research/` - Research & Análises
- **FEATURES.md** - Análise de features
- **PITFALLS.md** - Armadilhas e lições aprendidas
- **SUMMARY.md** - Summary de pesquisa

## Como Usar

**Para Desenvolvimento:** Leia a documentação relevante conforme necessário, começando por `/codebase/ARCHITECTURE.md`

**Para Onboarding:** Leia `PROJECT.md` → `ARCHITECTURE.md` → `STACK.md`

**Para Histórico:** Consulte `/phases/` para entender decisões de desenvolvimento

## Consolidação de Documentação
- ❌ STACK.md em `research/` foi removido (duplicate)
- ✅ ROADMAP.md na raiz é o source of truth
- ✅ Documentação de fases mantida como histórico

## Nota
Esta documentação é **informativa** e não é necessária para executar o projeto. Para instruções de setup, veja o README.md na raiz do projeto.
