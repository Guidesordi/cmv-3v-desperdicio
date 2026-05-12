# 🚀 Deploy do Dashboard de Desperdício — Streamlit Cloud

Guia completo pra colocar o dashboard online (acesso pros gerentes), com auth Google e free tier.

---

## ✅ O que esse app faz

- Lê a planilha de desperdício do **Google Forms** (já pública via export CSV)
- Mostra: KPIs · por motivo · top produtos · tendência · tabela com busca
- Filtros: unidade, período, tipo de motivo
- **Mobile-friendly** (responsivo)
- **Sem credenciais sensíveis** — só lê CSV público, não conecta no Atlas
- Cache de 10 min (botão "🔄 Atualizar" força reload)

---

## 🧪 Testar local primeiro

```bash
cd desperdicio_app
pip install -r requirements.txt
streamlit run app.py
```

Abre `http://localhost:8501`. Se funcionar, segue pro deploy.

---

## 🌐 Deploy no Streamlit Community Cloud (gratuito)

### Passo 1 — Repo no GitHub

A pasta `desperdicio_app/` precisa estar em um repositório GitHub.

**Opção A — Repo separado (recomendado, mais limpo):**

```bash
cd "C:/Users/guilh/Meu Drive/Claude Code/CMV-3V/desperdicio_app"
git init
git add app.py requirements.txt README_DEPLOY.md .streamlit
git commit -m "App de desperdício pros gerentes"
# Criar repo "cmv-3v-desperdicio" no GitHub (PRIVADO) e:
git remote add origin https://github.com/SEU_USUARIO/cmv-3v-desperdicio.git
git push -u origin main
```

**Opção B — Mesma pasta da ferramenta CMV-3V (mais simples se já tem repo):**

Faz commit do `desperdicio_app/` no repo CMV-3V existente. No deploy aponta pra subpasta.

### Passo 2 — Conectar ao Streamlit Cloud

1. Vai em [https://share.streamlit.io/](https://share.streamlit.io/)
2. Loga com sua conta Google
3. Clica **"New app"**
4. Preenche:
   - **Repository:** `SEU_USUARIO/cmv-3v-desperdicio`
   - **Branch:** `main`
   - **Main file path:** `app.py` (se Opção A) OU `desperdicio_app/app.py` (Opção B)
   - **App URL:** escolhe algo tipo `cmv-3v-desperdicio` → vira `https://cmv-3v-desperdicio.streamlit.app`
5. **Advanced settings**:
   - Python version: `3.11` ou `3.12`
   - Não precisa secrets (a planilha é pública)
6. **Deploy!**

Em ~2 minutos a app está no ar.

### Passo 3 — Restringir acesso (auth Google)

Por padrão a URL é pública. Pra restringir aos gerentes:

1. No dashboard do Streamlit Cloud, clica nos `⋮` do seu app → **Settings**
2. Aba **"Sharing"**
3. Ativa **"Private app"**
4. Em **"Email allowlist"** adiciona os 6 emails dos gerentes (um por linha):
   ```
   gerente.iac@gmail.com
   gerente.ian@gmail.com
   gerente.ias@gmail.com
   gerente.koj@gmail.com
   gerente.mane@gmail.com
   gerente.sqn@gmail.com
   guilhermedesordi@gmail.com
   ```
5. Salva.

Agora **só esses emails Google conseguem entrar**. Quando o gerente abrir a URL pela primeira vez, vai pedir login Google.

> ⚠️ **Email pessoal funciona normal.** Não precisa ser corporativo. Streamlit Cloud autentica via OAuth Google em qualquer email.

### Passo 4 — Compartilhar com os gerentes

Mensagem-modelo:

```
Pessoal, dashboard de desperdício do Grupo 3V:

🔗 https://cmv-3v-desperdicio.streamlit.app

Pra acessar, basta logar com a conta Google de vocês
(o email que vocês me passaram).

Funciona no celular também. Atualiza automaticamente
a cada 10 minutos — se quiserem forçar, clicam em
"🔄 Atualizar dados" no menu lateral.

Qualquer dúvida me chamam.
```

---

## 🔄 Atualizar o app no futuro

Toda vez que editar `app.py` (ou outros):
```bash
git add .
git commit -m "Descrição da mudança"
git push
```
Streamlit Cloud detecta o push e **redeploya automaticamente em ~1 min**.

---

## 💡 Limitações do free tier

- **1 GB RAM** (sobra muito pra esse app — usa <100 MB)
- **App dorme após 7 dias sem acesso** (acorda em ~30s na 1ª visita)
- **3 apps privados gratuitos** por conta

Se passar 3 apps OU precisar mais RAM: upgrade pra **Teams ($25/mês)** ou migrar pra Railway/VPS.

---

## 🐛 Troubleshooting

### "Module not found"
→ Faltou listar a lib em `requirements.txt`. Adiciona e push.

### Dashboard vazio
→ Verifica se a planilha Google Forms está pública.
URL teste: `https://docs.google.com/spreadsheets/d/1qX36AZptjemPuwzoYq9n3QB7AD3NibhSizLXG9BtFKM/export?format=csv&gid=2068526568`
Tem que retornar CSV sem pedir login.

### "Out of memory"
→ Não deve acontecer com esse app (é leve). Se acontecer, simplifica cálculos
ou aumenta TTL do cache.

### Gerente não consegue logar
→ Verifica se o email dele está na allowlist EXATAMENTE como ele usa no Google.
Email com typo (`.com.br` vs `.com`) bloqueia.

---

## 📁 Arquivos do app

```
desperdicio_app/
├── app.py                  ← dashboard (1 arquivo, single-page)
├── requirements.txt        ← libs Python
├── .streamlit/
│   └── config.toml         ← tema escuro, otimizado mobile
└── README_DEPLOY.md        ← este arquivo
```
