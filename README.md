## Bot Telegram de Promoções AliExpress (Versão Básica)

### Requisitos
- Python 3.11+
- Conta no Telegram (token do BotFather)
- Canal `@SJPROMOS` (o bot precisa ser admin do canal)

### Variáveis de ambiente
Crie um arquivo `.env` baseado em `.env.example` ou defina no provedor de deploy.

### Instalação local
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Simulação (teste rápido)
Executa 1 hora simulada com N=5 postagens:
```bash
python simulate_hour.py
```

### Deploy no Render (grátis)
1. Crie novo serviço Web (ou Background Worker) apontando para este repositório.
2. Defina as variáveis de ambiente do `.env.example` no painel do Render.
3. Comando de start: `python main.py`
4. Tipo: `Background Worker` (para rodar 24/7).

### Ajustes de operação
- Comando `/status`: estado do bot e últimas postagens.
- Comando `/pausar` e `/retomar`.
- Comando `/freq min max`: altera faixa de postagens por hora.
  - Ex.: `/freq 20 25`

### Trocar canal ou tracking
- `CHANNEL_ID` no `.env` (ex.: `@SJPROMOS`).
- `TRACKING_ID` no `.env` (qualquer string). 

### Observações
- O cliente da AliExpress usa um fallback de dados mock enquanto as credenciais reais/integração oficial não estão disponibilizadas. A estrutura já contempla: score por desconto/cupom/vendas/frete, filtro de categorias e geração de link afiliado com encurtador simples.
- Banco SQLite local (`data/bot.sqlite3`).
- Logs em `logs/bot.log` + console.


