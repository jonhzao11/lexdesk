# LEXDESK

Plataforma de estudo e prática jurídica para estudantes de Direito em Portugal.

Site: https://jonhzao11.github.io/lexdesk/

## Robôs de teste

Três robôs percorrem o site todos os dias e a cada publicação (`.github/workflows/robos.yml`):

- **Robô Explorador** — todas as páginas, no computador e no telemóvel, em modo claro e escuro, e os botões de cada página;
- **Robô Calculista** — as calculadoras jurídicas, com valores normais, extremos e inválidos, e resultados conhecidos;
- **Robô Estudante** — uma simulação de exame, uma sessão de flashcards e os casos práticos.

Usam uma base de dados simulada (`tests/mock_supabase.js`) e nunca tocam nos dados reais. O relatório fica no resumo de cada execução e, se houver problemas, abre-se um aviso (issue). Com o segredo `ROBOS_TOKEN` definido, os robôs somam pontos no ranking (até 30 por dia cada um, assinalados como «Robô de teste») e o relatório inclui os erros registados no navegador dos utilizadores nas últimas 24 horas.

Para correr localmente: `pip install playwright && python -m playwright install chromium && python tests/robos.py`.
